import logging,time
from sqlalchemy.orm import Session
from app.agents.context import AgentContextBuilder
from app.agents.errors import AgentInvalidPlanError,AgentLLMError,AgentLLMNotConfiguredError,AgentNotFoundError
from app.agents.runtime import AgentRuntime
from app.agents.schemas import AgentFinalResponse,AgentPlan,AgentRunList,AgentRunRead,AgentRunResponse,AgentStepRead
from app.agents.validator import AgentPlanValidator
from app.config import Settings
from app.exceptions import DatasetNotFoundError,LLMInvalidResponseError,LLMNotConfiguredError,LLMProviderError
from app.models import AgentRun,AgentRunStatus
from app.repositories import AgentRunRepository,DatasetProfileRepository,DatasetRepository
logger=logging.getLogger(__name__)
class PlannerAgentService:
    def __init__(self,session:Session,settings:Settings,provider,runtime_factory)->None:self.session=session;self.settings=settings;self.provider=provider;self.runtime_factory=runtime_factory;self.runs=AgentRunRepository(session);self.datasets=DatasetRepository(session);self.profiles=DatasetProfileRepository(session)
    def run(self,dataset_id:str,question:str)->AgentRunResponse:
        dataset=self.datasets.get_by_id(dataset_id)
        if dataset is None:raise DatasetNotFoundError("Dataset 不存在")
        if getattr(self.provider,"is_configured",True) is False:raise AgentLLMNotConfiguredError("Agent requires an LLM provider configuration.")
        record=self.runs.create(dataset_id,question);record.status=AgentRunStatus.PLANNING;self.session.commit();started=time.perf_counter()
        try:
            context=AgentContextBuilder(self.settings).build(dataset,self.profiles.get_by_dataset_id(dataset_id));record.context_metadata_json=context.metadata
            plan=self.provider.generate_plan(question,context.payload)
            if not isinstance(plan,AgentPlan):plan=AgentPlan.model_validate(plan)
            planner_ms=round((time.perf_counter()-started)*1000,3);record.context_metadata_json={**context.metadata,"planner_duration_ms":planner_ms};record.goal=plan.goal;record.planner_summary=plan.summary;record.step_count=len(plan.steps);record.status=AgentRunStatus.VALIDATING;self.session.commit();logger.info("agent_run_id=%s dataset_id=%s planner_duration_ms=%s steps=%s",record.id,dataset_id,planner_ms,len(plan.steps))
            context_columns=context.payload.get("profile",{}).get("columns",[])
            column_types={x["name"]:str(x.get("semantic_type") or x.get("physical_dtype") or "") for x in context_columns}
            if not column_types:column_types={x["name"]:str(x.get("dtype","")) for x in dataset.metadata_json.get("columns",[])}
            AgentPlanValidator(self.settings).validate(plan,column_types)
            final=self.runtime_factory().execute(record,plan);self.session.refresh(record);return AgentRunResponse(run=run_read(record,self.runs.steps(record.id)),plan=plan,final=final)
        except LLMNotConfiguredError as exc:
            self._fail(record,"AGENT_LLM_NOT_CONFIGURED",exc.detail);raise AgentLLMNotConfiguredError(exc.detail) from exc
        except (LLMInvalidResponseError,LLMProviderError) as exc:
            self._fail(record,"AGENT_LLM_ERROR",exc.detail);raise AgentLLMError(exc.detail) from exc
        except AgentInvalidPlanError as exc:
            self._fail(record,exc.code,exc.detail);raise
        except Exception as exc:
            self._fail(record,"AGENT_EXECUTION_FAILED","Agent execution failed.");raise
    def _fail(self,record:AgentRun,code:str,message:str)->None:record.status=AgentRunStatus.FAILED;record.error_code=code;record.error_message=message;self.session.commit()
    def list(self,dataset_id:str,page:int,page_size:int):
        if self.datasets.get_by_id(dataset_id) is None:raise DatasetNotFoundError("Dataset 不存在")
        return self.runs.list(dataset_id,page,page_size)
    def get(self,dataset_id:str,run_id:str)->AgentRun:
        if self.datasets.get_by_id(dataset_id) is None:raise DatasetNotFoundError("Dataset 不存在")
        record=self.runs.get(dataset_id,run_id)
        if record is None:raise AgentNotFoundError("Agent Run 不存在")
        return record
    def read(self,record:AgentRun)->AgentRunRead:return run_read(record,self.runs.steps(record.id))
def run_read(record:AgentRun,steps)->AgentRunRead:
    return AgentRunRead(id=record.id,dataset_id=record.dataset_id,user_question=record.user_question,goal=record.goal,status=record.status,planner_summary=record.planner_summary,step_count=record.step_count,completed_step_count=record.completed_step_count,final_summary_json=record.final_summary_json,error_code=record.error_code,error_message=record.error_message,context_metadata_json=record.context_metadata_json,created_at=record.created_at,updated_at=record.updated_at,steps=[AgentStepRead(id=x.id,step_id=x.step_id,sequence=x.sequence,tool_name=x.tool_name,purpose=x.purpose,status=x.status,input_summary_json=x.input_summary_json,output_summary_json=x.output_summary_json,artifact_type=x.artifact_type,artifact_id=x.artifact_id,execution_time_ms=x.execution_time_ms,error_code=x.error_code,error_message=x.error_message,created_at=x.created_at,updated_at=x.updated_at) for x in steps])
