from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.profile_service import DatasetProfileService
from app.profiling.types import ProfileResult
from app.schemas import DatasetListResponse, DatasetPreview, DatasetProfileRead, DatasetRead, HealthResponse
from app.services import DatasetService
from app.query.provider import LLMProvider, OpenAICompatibleProvider
from app.query.schemas import AnalysisQueryRead, QueryCreate, QueryListResponse, QueryResponse
from app.query.service import NaturalLanguageSQLService, query_read
from app.analysis.schemas import AnalysisListResponse, AnalysisPlan, AnalysisResponse, AnalysisRunRead
from app.analysis.service import StructuredAnalysisService, run_read
from app.analysis.process import AnalysisProcessRunner
from app.charts.schemas import ChartListResponse, ChartRead, ChartResult, ChartSpec
from app.charts.service import ChartService, chart_read
from app.agents.runtime import AgentRuntime
from app.agents.schemas import AgentCreate,AgentRunList,AgentRunRead,AgentRunResponse
from app.agents.service import PlannerAgentService
from app.agents.tools import AnalysisToolAdapter,ChartToolAdapter,SQLToolAdapter,ToolRegistry

router = APIRouter()


def service_dependency(session: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> DatasetService:
    return DatasetService(session, settings)


def profile_service_dependency(session: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> DatasetProfileService:
    return DatasetProfileService(session, settings)


def get_llm_provider(settings: Settings = Depends(get_settings)) -> LLMProvider:
    return OpenAICompatibleProvider(settings)


def query_service_dependency(session: Session = Depends(get_db), settings: Settings = Depends(get_settings), provider: LLMProvider = Depends(get_llm_provider)) -> NaturalLanguageSQLService:
    return NaturalLanguageSQLService(session, settings, provider)


def get_analysis_runner(settings: Settings = Depends(get_settings)) -> AnalysisProcessRunner:
    return AnalysisProcessRunner(settings)


def analysis_service_dependency(session: Session = Depends(get_db), settings: Settings = Depends(get_settings), runner: AnalysisProcessRunner = Depends(get_analysis_runner)) -> StructuredAnalysisService:
    return StructuredAnalysisService(session, settings, runner)

def chart_service_dependency(session: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> ChartService:
    return ChartService(session, settings)

def agent_service_dependency(session:Session=Depends(get_db),settings:Settings=Depends(get_settings),provider:LLMProvider=Depends(get_llm_provider),runner:AnalysisProcessRunner=Depends(get_analysis_runner))->PlannerAgentService:
    query_service=NaturalLanguageSQLService(session,settings,provider);analysis_service=StructuredAnalysisService(session,settings,runner);chart_service=ChartService(session,settings)
    registry=ToolRegistry([SQLToolAdapter(query_service,settings.agent_max_intermediate_rows,settings.agent_max_intermediate_cells),AnalysisToolAdapter(analysis_service,settings.agent_max_intermediate_rows,settings.agent_max_intermediate_cells),ChartToolAdapter(chart_service)])
    return PlannerAgentService(session,settings,provider,lambda:AgentRuntime(session,settings,registry,provider))


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


@router.post("/datasets/{dataset_id}/queries", response_model=QueryResponse)
def run_dataset_query(dataset_id: str, payload: QueryCreate, service: NaturalLanguageSQLService = Depends(query_service_dependency)) -> QueryResponse:
    return service.run(dataset_id, payload.question)


@router.get("/datasets/{dataset_id}/queries", response_model=QueryListResponse)
def list_dataset_queries(dataset_id: str, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), service: NaturalLanguageSQLService = Depends(query_service_dependency)) -> QueryListResponse:
    items, total = service.list(dataset_id, page, page_size)
    return QueryListResponse(items=[query_read(item) for item in items], total=total, page=page, page_size=page_size)


@router.get("/datasets/{dataset_id}/queries/{query_id}", response_model=AnalysisQueryRead)
def get_dataset_query(dataset_id: str, query_id: str, service: NaturalLanguageSQLService = Depends(query_service_dependency)) -> AnalysisQueryRead:
    return query_read(service.get(dataset_id, query_id))


@router.post("/datasets/{dataset_id}/analyses", response_model=AnalysisResponse)
def run_dataset_analysis(dataset_id: str, plan: AnalysisPlan, service: StructuredAnalysisService = Depends(analysis_service_dependency)) -> AnalysisResponse:
    return service.execute(dataset_id, plan)


@router.get("/datasets/{dataset_id}/analyses", response_model=AnalysisListResponse)
def list_dataset_analyses(dataset_id: str, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), service: StructuredAnalysisService = Depends(analysis_service_dependency)) -> AnalysisListResponse:
    items,total=service.list(dataset_id,page,page_size); return AnalysisListResponse(items=[run_read(item) for item in items],total=total,page=page,page_size=page_size)


@router.get("/datasets/{dataset_id}/analyses/{analysis_id}", response_model=AnalysisRunRead)
def get_dataset_analysis(dataset_id: str, analysis_id: str, service: StructuredAnalysisService = Depends(analysis_service_dependency)) -> AnalysisRunRead:
    return run_read(service.get(dataset_id,analysis_id))

@router.post("/datasets/{dataset_id}/charts", response_model=ChartResult, status_code=status.HTTP_201_CREATED)
def create_dataset_chart(dataset_id: str, spec: ChartSpec, service: ChartService = Depends(chart_service_dependency)) -> ChartResult:
    return service.create(dataset_id,spec)

@router.get("/datasets/{dataset_id}/charts", response_model=ChartListResponse)
def list_dataset_charts(dataset_id: str, page: int=Query(1,ge=1), page_size: int=Query(20,ge=1,le=100), service: ChartService=Depends(chart_service_dependency)) -> ChartListResponse:
    items,total=service.list(dataset_id,page,page_size); return ChartListResponse(items=[chart_read(x) for x in items],total=total,page=page,page_size=page_size)

@router.get("/datasets/{dataset_id}/charts/{chart_id}", response_model=ChartRead)
def get_dataset_chart(dataset_id: str, chart_id: str, service: ChartService=Depends(chart_service_dependency)) -> ChartRead:
    return chart_read(service.get(dataset_id,chart_id))

@router.delete("/datasets/{dataset_id}/charts/{chart_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dataset_chart(dataset_id: str, chart_id: str, service: ChartService=Depends(chart_service_dependency)) -> Response:
    service.delete(dataset_id,chart_id); return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post("/datasets/{dataset_id}/agent-runs",response_model=AgentRunResponse,status_code=status.HTTP_201_CREATED)
def create_agent_run(dataset_id:str,payload:AgentCreate,service:PlannerAgentService=Depends(agent_service_dependency))->AgentRunResponse:return service.run(dataset_id,payload.question)

@router.get("/datasets/{dataset_id}/agent-runs",response_model=AgentRunList)
def list_agent_runs(dataset_id:str,page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100),service:PlannerAgentService=Depends(agent_service_dependency))->AgentRunList:
    items,total=service.list(dataset_id,page,page_size);return AgentRunList(items=[service.read(x) for x in items],total=total,page=page,page_size=page_size)

@router.get("/datasets/{dataset_id}/agent-runs/{agent_run_id}",response_model=AgentRunRead)
def get_agent_run(dataset_id:str,agent_run_id:str,service:PlannerAgentService=Depends(agent_service_dependency))->AgentRunRead:return service.read(service.get(dataset_id,agent_run_id))


@router.delete("/datasets/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dataset(dataset_id: str, service: DatasetService = Depends(service_dependency)) -> Response:
    service.delete(dataset_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
