from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import Settings
from app.exceptions import DatasetNotFoundError, ProfileGenerationError, ProfileNotFoundError
from app.models import DatasetProfile, ProfileStatus
from app.parsers import load_dataframe
from app.profiling.service import ProfilingService
from app.profiling.types import ProfileResult
from app.repositories import DatasetProfileRepository, DatasetRepository


class DatasetProfileService:
    def __init__(self, session: Session, settings: Settings, owner_user_id: str | None = None) -> None:
        self.session = session
        self.settings = settings
        self.datasets = DatasetRepository(session, owner_user_id)
        self.profiles = DatasetProfileRepository(session)

    def get(self, dataset_id: str) -> DatasetProfile:
        if self.datasets.get_by_id(dataset_id) is None:
            raise DatasetNotFoundError("Dataset 不存在")
        profile = self.profiles.get_by_dataset_id(dataset_id)
        if profile is None:
            raise ProfileNotFoundError("Dataset Profile 尚未生成")
        return profile

    def generate(self, dataset_id: str) -> DatasetProfile:
        dataset = self.datasets.get_by_id(dataset_id)
        if dataset is None:
            raise DatasetNotFoundError("Dataset 不存在")
        profile = self.profiles.get_or_create(dataset_id)
        profile.status = ProfileStatus.RUNNING
        profile.error_message = None
        self.session.commit()

        try:
            upload_dir = self.settings.resolved_upload_dir
            path = (upload_dir / dataset.stored_filename).resolve()
            if path.parent != upload_dir or not path.is_file():
                raise FileNotFoundError("managed dataset file is missing")
            frame, _ = load_dataframe(path.read_bytes(), dataset.file_type)
            result = ProfilingService(self.settings).profile(frame)
            self._store_result(profile, result)
            self.session.commit()
            self.session.refresh(profile)
            return profile
        except Exception as exc:
            self.session.rollback()
            failed = self.profiles.get_or_create(dataset_id)
            failed.status = ProfileStatus.FAILED
            failed.error_message = "Dataset profiling failed. Verify that the managed file is readable."
            failed.profile_json = {}
            self.session.commit()
            raise ProfileGenerationError(failed.error_message) from exc

    @staticmethod
    def _store_result(profile: DatasetProfile, result: ProfileResult) -> None:
        summary = result.summary
        profile.status = ProfileStatus.READY
        profile.row_count = summary.row_count
        profile.column_count = summary.column_count
        profile.duplicate_row_count = summary.duplicate_row_count
        profile.duplicate_row_ratio = summary.duplicate_row_ratio
        profile.missing_cell_count = summary.missing_cell_count
        profile.missing_cell_ratio = summary.missing_cell_ratio
        profile.quality_score = summary.quality_score
        profile.generated_at = datetime.now(timezone.utc)
        profile.profile_json = result.model_dump(mode="json")
        profile.error_message = None
