from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Dataset, DatasetStatus


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
