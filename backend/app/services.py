import logging
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.config import Settings
from app.exceptions import DatasetNotFoundError, FileTooLargeError, InvalidFileError
from app.models import Dataset, DatasetStatus
from app.parsers import ParsedDataset, parse_dataset
from app.repositories import DatasetRepository

logger = logging.getLogger(__name__)
ALLOWED_TYPES = {".csv": "csv", ".xlsx": "xlsx"}
ALLOWED_MIME_TYPES = {
    "csv": {"text/csv", "application/csv", "application/vnd.ms-excel", "text/plain", "application/octet-stream"},
    "xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/octet-stream"},
}


class DatasetService:
    def __init__(self, session: Session, settings: Settings, owner_user_id: str | None = None) -> None:
        self.session = session
        self.settings = settings
        self.owner_user_id = owner_user_id
        self.repository = DatasetRepository(session, owner_user_id)
        self.upload_dir = settings.resolved_upload_dir

    async def upload(self, file: UploadFile) -> Dataset:
        original_filename = Path(file.filename or "").name
        suffix = Path(original_filename).suffix.lower()
        file_type = ALLOWED_TYPES.get(suffix)
        if not original_filename or not file_type:
            raise InvalidFileError("仅支持 .csv 和 .xlsx 文件")
        if file.content_type and file.content_type not in ALLOWED_MIME_TYPES[file_type]:
            raise InvalidFileError("文件 MIME 类型与扩展名不匹配")
        content = await file.read(self.settings.max_upload_size + 1)
        if not content:
            raise InvalidFileError("文件不能为空")
        if len(content) > self.settings.max_upload_size:
            raise FileTooLargeError(f"文件不能超过 {self.settings.max_upload_mb} MB")
        count, used_bytes = self.repository.usage()
        if count >= self.settings.max_datasets_per_user:
            raise InvalidFileError("Dataset 数量已达到账户上限")
        if used_bytes + len(content) > self.settings.max_storage_bytes_per_user:
            raise FileTooLargeError("账户存储空间不足")

        parsed = parse_dataset(content, file_type, self.settings.preview_row_limit)
        stored_filename = f"{uuid4().hex}{suffix}"
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        destination = (self.upload_dir / stored_filename).resolve()
        if destination.parent != self.upload_dir:
            raise InvalidFileError("无效文件路径")
        dataset = Dataset(
            owner_user_id=self.owner_user_id,
            name=Path(original_filename).stem[:255], original_filename=original_filename[:255], stored_filename=stored_filename,
            file_type=file_type, file_size=len(content), row_count=parsed.row_count, column_count=parsed.column_count,
            status=DatasetStatus.READY, metadata_json=parsed.metadata,
        )
        try:
            destination.write_bytes(content)
            self.repository.create(dataset)
            self.session.commit()
            self.session.refresh(dataset)
            return dataset
        except Exception:
            self.session.rollback()
            destination.unlink(missing_ok=True)
            raise

    def list(self, page: int, page_size: int) -> tuple[list[Dataset], int]:
        return self.repository.list(page, page_size)

    def get(self, dataset_id: str) -> Dataset:
        dataset = self.repository.get_by_id(dataset_id)
        if dataset is None:
            raise DatasetNotFoundError("Dataset 不存在")
        return dataset

    def preview(self, dataset_id: str) -> tuple[Dataset, ParsedDataset]:
        dataset = self.get(dataset_id)
        path = (self.upload_dir / dataset.stored_filename).resolve()
        if path.parent != self.upload_dir or not path.is_file():
            raise DatasetNotFoundError("Dataset 原始文件不存在")
        return dataset, parse_dataset(path.read_bytes(), dataset.file_type, self.settings.preview_row_limit)

    def delete(self, dataset_id: str) -> None:
        dataset = self.get(dataset_id)
        path = (self.upload_dir / dataset.stored_filename).resolve()
        self.repository.delete(dataset)
        self.session.commit()
        if path.parent == self.upload_dir:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                logger.warning("Dataset %s metadata deleted but file cleanup failed", dataset_id, exc_info=True)
