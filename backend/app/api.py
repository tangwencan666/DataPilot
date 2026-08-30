from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.schemas import DatasetListResponse, DatasetPreview, DatasetRead, HealthResponse
from app.services import DatasetService

router = APIRouter()


def service_dependency(session: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> DatasetService:
    return DatasetService(session, settings)


@router.get("/health", response_model=HealthResponse)
def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(status="ok", service=settings.app_name, environment=settings.app_env)


@router.post("/datasets", response_model=DatasetRead, status_code=status.HTTP_201_CREATED)
async def upload_dataset(file: UploadFile = File(...), service: DatasetService = Depends(service_dependency)) -> DatasetRead:
    return DatasetRead.model_validate(await service.upload(file))


@router.get("/datasets", response_model=DatasetListResponse)
def list_datasets(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), service: DatasetService = Depends(service_dependency)) -> DatasetListResponse:
    items, total = service.list(page, page_size)
    return DatasetListResponse(items=[DatasetRead.model_validate(item) for item in items], total=total, page=page, page_size=page_size)


@router.get("/datasets/{dataset_id}", response_model=DatasetRead)
def get_dataset(dataset_id: str, service: DatasetService = Depends(service_dependency)) -> DatasetRead:
    return DatasetRead.model_validate(service.get(dataset_id))


@router.get("/datasets/{dataset_id}/preview", response_model=DatasetPreview)
def get_dataset_preview(dataset_id: str, service: DatasetService = Depends(service_dependency)) -> DatasetPreview:
    dataset, parsed = service.preview(dataset_id)
    return DatasetPreview(dataset_id=dataset.id, filename=dataset.original_filename, row_count=parsed.row_count,
        column_count=parsed.column_count, columns=parsed.columns, preview_rows=parsed.preview_rows,
        preview_limit=service.settings.preview_row_limit)


@router.delete("/datasets/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dataset(dataset_id: str, service: DatasetService = Depends(service_dependency)) -> Response:
    service.delete(dataset_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
