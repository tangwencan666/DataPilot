from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AgentRun, AgentRunStatus, AgentStepRun, AgentStepStatus, AnalysisQuery, AnalysisRun, AnalysisRunStatus, Chart, ChartSourceType, ChartStatus, Dataset, DatasetProfile, DatasetStatus, ProfileStatus, QueryStatus


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


class AnalysisRunRepository:
    def __init__(self, session: Session) -> None: self.session = session

    def create(self, dataset_id: str, request_json: dict, operation_count: int) -> AnalysisRun:
        run = AnalysisRun(dataset_id=dataset_id, request_json=request_json, result_summary_json={}, operation_count=operation_count, status=AnalysisRunStatus.PENDING)
        self.session.add(run); self.session.flush(); return run

    def get(self, dataset_id: str, run_id: str) -> AnalysisRun | None:
        return self.session.scalar(select(AnalysisRun).where(AnalysisRun.dataset_id == dataset_id, AnalysisRun.id == run_id))

    def list(self, dataset_id: str, page: int, page_size: int) -> tuple[list[AnalysisRun], int]:
        condition = AnalysisRun.dataset_id == dataset_id; total = self.session.scalar(select(func.count()).select_from(AnalysisRun).where(condition)) or 0
        statement = select(AnalysisRun).where(condition).order_by(AnalysisRun.created_at.desc(), AnalysisRun.id.desc()).offset((page-1)*page_size).limit(page_size)
        return list(self.session.scalars(statement)), total


class ChartRepository:
    def __init__(self, session: Session) -> None: self.session = session

    def create(self, dataset_id: str, spec: dict) -> Chart:
        chart = Chart(dataset_id=dataset_id, source_type=ChartSourceType.DATASET, chart_type=spec["type"], title=spec["title"], spec_json=spec, status=ChartStatus.PENDING)
        self.session.add(chart); self.session.flush(); return chart

    def get(self, dataset_id: str, chart_id: str) -> Chart | None:
        return self.session.scalar(select(Chart).where(Chart.dataset_id == dataset_id, Chart.id == chart_id))

    def list(self, dataset_id: str, page: int, page_size: int) -> tuple[list[Chart], int]:
        condition = Chart.dataset_id == dataset_id
        total = self.session.scalar(select(func.count()).select_from(Chart).where(condition)) or 0
        stmt = select(Chart).where(condition).order_by(Chart.created_at.desc(), Chart.id.desc()).offset((page-1)*page_size).limit(page_size)
        return list(self.session.scalars(stmt)), total

    def delete(self, chart: Chart) -> None: self.session.delete(chart)

class AgentRunRepository:
    def __init__(self,session:Session)->None:self.session=session
    def create(self,dataset_id:str,question:str)->AgentRun:
        record=AgentRun(dataset_id=dataset_id,user_question=question,status=AgentRunStatus.PENDING,final_summary_json={},context_metadata_json={});self.session.add(record);self.session.flush();return record
    def get(self,dataset_id:str,run_id:str)->AgentRun|None:return self.session.scalar(select(AgentRun).where(AgentRun.dataset_id==dataset_id,AgentRun.id==run_id))
    def list(self,dataset_id:str,page:int,page_size:int)->tuple[list[AgentRun],int]:
        condition=AgentRun.dataset_id==dataset_id;total=self.session.scalar(select(func.count()).select_from(AgentRun).where(condition)) or 0
        stmt=select(AgentRun).where(condition).order_by(AgentRun.created_at.desc(),AgentRun.id.desc()).offset((page-1)*page_size).limit(page_size);return list(self.session.scalars(stmt)),total
    def create_step(self,run_id:str,step_id:str,sequence:int,tool:str,purpose:str,input_summary:dict)->AgentStepRun:
        item=AgentStepRun(agent_run_id=run_id,step_id=step_id,sequence=sequence,tool_name=tool,purpose=purpose,status=AgentStepStatus.PENDING,input_summary_json=input_summary,output_summary_json={});self.session.add(item);self.session.flush();return item
    def steps(self,run_id:str):return list(self.session.scalars(select(AgentStepRun).where(AgentStepRun.agent_run_id==run_id).order_by(AgentStepRun.sequence)))
