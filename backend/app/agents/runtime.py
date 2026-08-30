import logging,time
from sqlalchemy.orm import Session
from app.agents.errors import AgentTimeoutError
from app.agents.schemas import AgentArtifact,AgentFinalResponse,AgentPlan,ToolExecutionResult,ToolName
from app.agents.tools import ToolRegistry
from app.config import Settings
from app.exceptions import DatasetError
from app.models import AgentRun,AgentRunStatus,AgentStepStatus
from app.repositories import AgentRunRepository
logger=logging.getLogger(__name__)

class AgentRuntime:
    def __init__(self,session:Session,settings:Settings,registry:ToolRegistry,provider)->None:self.session=session;self.settings=settings;self.registry=registry;self.provider=provider;self.repo=AgentRunRepository(session)
    def execute(self,record:AgentRun,plan:AgentPlan)->AgentFinalResponse|None:
        started=time.monotonic();statuses:dict[str,AgentStepStatus]={};results:list[tuple[str,ToolExecutionResult]]=[]
        record.status=AgentRunStatus.RUNNING;self.session.commit()
        for sequence,step in enumerate(plan.steps,1):
            persisted=self.repo.create_step(record.id,step.id,sequence,step.tool,step.purpose,step.input.model_dump(mode="json"));self.session.commit()
            if any(statuses.get(dep)!=AgentStepStatus.SUCCEEDED for dep in step.depends_on):
                persisted.status=AgentStepStatus.SKIPPED;persisted.error_code="AGENT_DEPENDENCY_FAILED";persisted.error_message="A dependency did not succeed.";statuses[step.id]=persisted.status;self.session.commit();continue
            if time.monotonic()-started>=self.settings.agent_timeout_seconds:
                persisted.status=AgentStepStatus.SKIPPED;persisted.error_code="AGENT_TIMEOUT";persisted.error_message="Agent deadline reached before this step.";statuses[step.id]=persisted.status;self.session.commit();continue
            persisted.status=AgentStepStatus.RUNNING;self.session.commit();step_started=time.perf_counter();logger.info("agent_run_id=%s dataset_id=%s step_id=%s tool=%s status=RUNNING",record.id,record.dataset_id,step.id,step.tool)
            try:
                result=self.registry.get(ToolName(step.tool)).execute(record.dataset_id,step);persisted.status=AgentStepStatus.SUCCEEDED;persisted.output_summary_json=result.model_dump(mode="json");persisted.artifact_type=result.artifact_type;persisted.artifact_id=result.artifact_id;record.completed_step_count+=1;results.append((step.id,result))
            except DatasetError as exc:
                persisted.status=AgentStepStatus.FAILED;persisted.error_code=exc.code;persisted.error_message=exc.detail
            except Exception:
                persisted.status=AgentStepStatus.FAILED;persisted.error_code="AGENT_TOOL_FAILED";persisted.error_message="Tool execution failed.";logger.exception("agent_run_id=%s step_id=%s tool=%s failed",record.id,step.id,step.tool)
            persisted.execution_time_ms=round((time.perf_counter()-step_started)*1000,3);statuses[step.id]=persisted.status;self.session.commit();logger.info("agent_run_id=%s dataset_id=%s step_id=%s tool=%s status=%s duration_ms=%s",record.id,record.dataset_id,step.id,step.tool,persisted.status.value,persisted.execution_time_ms)
        succeeded=len(results);failed=any(x==AgentStepStatus.FAILED for x in statuses.values());timed_out=any(x.error_code=="AGENT_TIMEOUT" for x in self.repo.steps(record.id))
        if not succeeded:
            record.status=AgentRunStatus.FAILED;record.error_code="AGENT_TIMEOUT" if timed_out else "AGENT_EXECUTION_FAILED";record.error_message="No Agent step completed successfully.";self.session.commit();return None
        summaries=[{"step_id":sid,**result.model_dump(mode="json",exclude={"rows"}),"rows":result.rows[:10]} for sid,result in results]
        synth_started=time.perf_counter()
        try:
            final=self.provider.generate_final_summary(record.user_question,plan.summary,summaries)
            if not isinstance(final,AgentFinalResponse):final=AgentFinalResponse.model_validate(final)
            final=final.model_copy(update={"key_findings":final.key_findings[:self.settings.agent_max_final_findings],"used_tools":list(dict.fromkeys([r.tool for _,r in results])),"artifacts":[AgentArtifact(type=r.artifact_type,id=r.artifact_id,step_id=sid) for sid,r in results if r.artifact_type and r.artifact_id]})
            record.final_summary_json=final.model_dump(mode="json");record.status=AgentRunStatus.PARTIAL if failed or timed_out else AgentRunStatus.SUCCEEDED;self.session.commit();logger.info("agent_run_id=%s final_status=%s synthesis_duration_ms=%.3f",record.id,record.status.value,(time.perf_counter()-synth_started)*1000);return final
        except Exception:
            record.status=AgentRunStatus.PARTIAL;record.error_code="AGENT_FINAL_SYNTHESIS_FAILED";record.error_message="Final structured synthesis failed.";self.session.commit();logger.exception("agent_run_id=%s final_synthesis=FAILED",record.id);return None
