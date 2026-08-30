from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.profile_service import DatasetProfileService
from app.profiling.types import ProfileResult
from app.schemas import DatasetListResponse, DatasetPreview, DatasetProfileRead, DatasetRead, HealthResponse
from app.services import DatasetService

router = APIRouter()


def service_dependency(session: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> DatasetService:
    return DatasetService(session, settings)


def profile_service_dependency(session: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> DatasetProfileService:
    return DatasetProfileService(session, settings)


def profile_response(profile) -> DatasetProfileRead:
    return DatasetProfileRead(
        id=profile.id, dataset_id=profile.dataset_id, status=profile.status, profile_version=profile.profile_version,
        row_count=profile.row_count, column_count=profile.column_count, duplicate_row_count=profile.duplicate_row_count,
        duplicate_row_ratio=profile.duplicate_row_ratio, missing_cell_count=profile.missing_cell_count,
        missing_cell_ratio=profile.missing_cell_ratio, quality_score=profile.quality_score,
        generated_at=profile.generated_at, error_message=profile.error_message, created_at=profile.created_at,
        updated_at=profile.updated_at, profile=ProfileResult.model_validate(profile.profile_json) if profile.profile_json else None,
    )


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


@router.post("/datasets/{dataset_id}/profile", response_model=DatasetProfileRead)
def generate_dataset_profile(dataset_id: str, service: DatasetProfileService = Depends(profile_service_dependency)) -> DatasetProfileRead:
    return profile_response(service.generate(dataset_id))


@router.get("/datasets/{dataset_id}/profile", response_model=DatasetProfileRead)
def get_dataset_profile(dataset_id: str, service: DatasetProfileService = Depends(profile_service_dependency)) -> DatasetProfileRead:
    return profile_response(service.get(dataset_id))


@router.delete("/datasets/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dataset(dataset_id: str, service: DatasetService = Depends(service_dependency)) -> Response:
    service.delete(dataset_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
