from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AnalysisQuery, Dataset, DatasetProfile, DatasetStatus, ProfileStatus, QueryStatus


class DatasetRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, dataset: Dataset) -> Dataset:
        self.session.add(dataset)
        self.session.flush()
        return dataset

    def get_by_id(self, dataset_id: str) -> Dataset | None:
        return self.session.get(Dataset, dataset_id)

    def list(self, page: int, page_size: int) -> tuple[list[Dataset], int]:
        total = self.session.scalar(select(func.count()).select_from(Dataset)) or 0
        statement = select(Dataset).order_by(Dataset.created_at.desc(), Dataset.id.desc()).offset((page - 1) * page_size).limit(page_size)
        return list(self.session.scalars(statement)), total

    def delete(self, dataset: Dataset) -> None:
        self.session.delete(dataset)

    def update_status(self, dataset: Dataset, status: DatasetStatus) -> Dataset:
        dataset.status = status
        self.session.flush()
        return dataset


class DatasetProfileRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_dataset_id(self, dataset_id: str) -> DatasetProfile | None:
        return self.session.scalar(select(DatasetProfile).where(DatasetProfile.dataset_id == dataset_id))

    def get_or_create(self, dataset_id: str) -> DatasetProfile:
        profile = self.get_by_dataset_id(dataset_id)
        if profile is None:
            profile = DatasetProfile(dataset_id=dataset_id, status=ProfileStatus.PENDING)
            self.session.add(profile)
            self.session.flush()
        return profile


class AnalysisQueryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, dataset_id: str, question: str) -> AnalysisQuery:
        query = AnalysisQuery(dataset_id=dataset_id, question=question, status=QueryStatus.PENDING)
        self.session.add(query); self.session.flush()
        return query

    def get(self, dataset_id: str, query_id: str) -> AnalysisQuery | None:
        return self.session.scalar(select(AnalysisQuery).where(AnalysisQuery.dataset_id == dataset_id, AnalysisQuery.id == query_id))

    def list(self, dataset_id: str, page: int, page_size: int) -> tuple[list[AnalysisQuery], int]:
        condition = AnalysisQuery.dataset_id == dataset_id
        total = self.session.scalar(select(func.count()).select_from(AnalysisQuery).where(condition)) or 0
        statement = select(AnalysisQuery).where(condition).order_by(AnalysisQuery.created_at.desc(), AnalysisQuery.id.desc()).offset((page - 1) * page_size).limit(page_size)
        return list(self.session.scalars(statement)), total
