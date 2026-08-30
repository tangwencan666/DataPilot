from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router
from app.config import get_settings
from app.exceptions import DatasetError
from app.schemas import ErrorResponse
from fastapi.responses import JSONResponse

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api/v1")


@app.exception_handler(DatasetError)
def dataset_error_handler(_, exc: DatasetError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=ErrorResponse(detail=exc.detail).model_dump())


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"message": "DataPilot API", "docs": "/docs"}
