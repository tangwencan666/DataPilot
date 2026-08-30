import json
import logging
import time
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api import router
from app.config import get_settings
from app.exceptions import DatasetError
from app.schemas import ErrorResponse
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text

from app.database import get_db
from sqlalchemy.orm import Session
from fastapi import Depends
from app.rate_limit import limiter

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.9.0")
app.state.limiter = limiter


def rate_limit_handler(request: Request, _: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded", "code": "RATE_LIMIT_EXCEEDED", "request_id": getattr(request.state, "request_id", None)},
    )


app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api/v1")

REQUESTS = Counter("datapilot_http_requests_total", "HTTP requests", ["method", "path", "status"])
LATENCY = Histogram("datapilot_http_request_duration_seconds", "HTTP request latency", ["method", "path"])
logger = logging.getLogger("datapilot.request")


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", "")[:128] or str(uuid4())
    request.state.request_id = request_id
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Unhandled request failure", extra={"request_id": request_id})
        response = JSONResponse(
            status_code=500, content={"detail": "Internal server error", "code": "INTERNAL_ERROR", "request_id": request_id}
        )
    duration = time.perf_counter() - started
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    REQUESTS.labels(request.method, request.url.path, response.status_code).inc()
    LATENCY.labels(request.method, request.url.path).observe(duration)
    logger.info(
        json.dumps(
            {
                "request_id": request_id,
                "user_id": getattr(request.state, "user_id", None),
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration * 1000, 2),
            }
        )
    )
    return response


@app.exception_handler(DatasetError)
def dataset_error_handler(request: Request, exc: DatasetError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(detail=exc.detail, code=exc.code, request_id=getattr(request.state, "request_id", None)).model_dump(),
    )


@app.exception_handler(RequestValidationError)
def request_validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    code = "CHART_VALIDATION_FAILED" if "/charts" in request.url.path else "VALIDATION_ERROR"
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            detail="Request validation failed.", code=code, request_id=getattr(request.state, "request_id", None)
        ).model_dump(),
    )


@app.exception_handler(HTTPException)
def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    code = "AUTHENTICATION_REQUIRED" if exc.status_code == 401 else "HTTP_ERROR"
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": str(exc.detail), "code": code, "request_id": getattr(request.state, "request_id", None)},
        headers=exc.headers,
    )


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"message": "DataPilot API", "docs": "/docs"}


@app.get("/ready", include_in_schema=False)
def readiness(session: Session = Depends(get_db)) -> dict[str, str]:
    session.execute(text("SELECT 1"))
    return {"status": "ready"}


@app.get("/metrics", include_in_schema=False)
def metrics() -> PlainTextResponse:
    return PlainTextResponse(generate_latest().decode(), media_type=CONTENT_TYPE_LATEST)
