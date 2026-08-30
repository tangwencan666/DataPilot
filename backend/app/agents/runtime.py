import logging,time
from sqlalchemy.orm import Session
from app.agents.repair import RepairValidator,StepRepairService
from app.agents.schemas import AgentArtifact,AgentFinalResponse,AgentPlan,ToolName
from app.agents.observation import observe
from app.agents.tools import ToolRegistry
from app.config import Settings
from app.exceptions import DatasetError
from app.models import AgentRun,AgentRunStatus,AgentStepStatus
from app.repositories import AgentRunRepository
logger=logging.getLogger(__name__)
class AgentRuntime:
    def __init__(self,session:Session,settings:Settings,registry:ToolRegistry,provider,repair_context=None,column_types=None)->None:self.session=session;self.settings=settings;self.registry=registry;self.provider=provider;self.repo=AgentRunRepository(session);self.repair_context=repair_context or {};self.column_types=column_types or {}
    def _attempt(self,record,step,persisted,number,kind,run_repairs):
        attempt=self.repo.create_attempt(persisted.id,number,kind,step.input.model_dump(mode="json"));persisted.attempt_count+=1;self.session.commit();started=time.perf_counter();result=None;code=None;message=None
        try:result=self.registry.get(ToolName(step.tool)).execute(record.dataset_id,step)
        except DatasetError as exc:code=exc.code;message=exc.detail
        except Exception:code="AGENT_TOOL_FAILED";message="Tool execution failed.";logger.exception("agent_run_id=%s step_id=%s attempt=%s failed",record.id,step.id,number)
        obs=observe(step.id,ToolName(step.tool),result,code,message,self.settings,persisted.repair_count,run_repairs);attempt.execution_time_ms=round((time.perf_counter()-started)*1000,3);attempt.observation_json=obs.model_dump(mode="json");attempt.status="SUCCEEDED" if obs.success else "FAILED";attempt.error_code=code or ("EMPTY_RESULT" if not obs.success else None);attempt.error_message=message;persisted.final_attempt_id=attempt.id;self.session.commit()
        logger.info("agent_run_id=%s dataset_id=%s step_id=%s tool=%s attempt_number=%s attempt_type=%s failure_category=%s retryable=%s duration_ms=%s",record.id,record.dataset_id,step.id,step.tool,number,kind,obs.error_category.value,obs.retryable,attempt.execution_time_ms);return result if obs.success else None,obs,attempt
    def execute(self,record:AgentRun,plan:AgentPlan)->AgentFinalResponse|None:
        started=time.monotonic();statuses={};results=[];run_repairs=0;repair_success=0;repair_failure=0;record.status=AgentRunStatus.RUNNING;self.session.commit()
        for sequence,step in enumerate(plan.steps,1):
            persisted=self.repo.create_step(record.id,step.id,sequence,step.tool,step.purpose,step.input.model_dump(mode="json"));self.session.commit()
            if any(statuses.get(dep)!=AgentStepStatus.SUCCEEDED for dep in step.depends_on):persisted.status=AgentStepStatus.SKIPPED;persisted.error_code="AGENT_DEPENDENCY_FAILED";persisted.error_message="A dependency did not succeed.";statuses[step.id]=persisted.status;self.session.commit();continue
            if time.monotonic()-started>=self.settings.agent_timeout_seconds:persisted.status=AgentStepStatus.SKIPPED;persisted.error_code="AGENT_TIMEOUT";persisted.error_message="Agent deadline reached before this step.";statuses[step.id]=persisted.status;self.session.commit();continue
            persisted.status=AgentStepStatus.RUNNING;step_started=time.perf_counter();self.session.commit();result,obs,attempt=self._attempt(record,step,persisted,1,"INITIAL",run_repairs)
            if result is None and obs.retryable and time.monotonic()-started<self.settings.agent_timeout_seconds:
                repair_started=time.perf_counter();persisted.repair_count+=1;run_repairs+=1;self.session.commit()
                try:
                    repair=StepRepairService(self.provider,self.settings).repair(record.user_question,plan.summary,step,obs,self.repair_context);repaired=RepairValidator(self.settings).validate(step,repair,self.column_types)
                    if time.monotonic()-started>=self.settings.agent_timeout_seconds:raise TimeoutError("Agent deadline reached before retry.")
                    result,obs,retry_attempt=self._attempt(record,repaired,persisted,2,"REPAIR",run_repairs);retry_attempt.repair_summary_json={"summary":repair.repair_summary[:500]}
                    if result:repair_success+=1
                    else:repair_failure+=1
                    logger.info("agent_run_id=%s step_id=%s repair_status=%s repair_duration_ms=%.3f",record.id,step.id,"SUCCEEDED" if result else "FAILED",(time.perf_counter()-repair_started)*1000)
                except Exception:
                    repair_failure+=1;persisted.error_code="AGENT_REPAIR_FAILED";persisted.error_message="Structured repair generation or validation failed.";logger.warning("agent_run_id=%s step_id=%s repair_status=FAILED repair_duration_ms=%.3f",record.id,step.id,(time.perf_counter()-repair_started)*1000)
            if result:
                persisted.status=AgentStepStatus.SUCCEEDED;persisted.output_summary_json=result.model_dump(mode="json");persisted.artifact_type=result.artifact_type;persisted.artifact_id=result.artifact_id;record.completed_step_count+=1;results.append((step.id,result,persisted))
            else:persisted.status=AgentStepStatus.FAILED;persisted.error_code=persisted.error_code or obs.error_code or obs.error_category.value;persisted.error_message=persisted.error_message or obs.error_message or "Step did not produce a usable result."
            persisted.execution_time_ms=round((time.perf_counter()-step_started)*1000,3);statuses[step.id]=persisted.status;self.session.commit()
        record.context_metadata_json={**record.context_metadata_json,"initial_attempt_count":sum(x.attempt_count>0 for x in self.repo.steps(record.id)),"repair_attempt_count":run_repairs,"repair_success_count":repair_success,"repair_failure_count":repair_failure};succeeded=len(results);failed=any(x==AgentStepStatus.FAILED for x in statuses.values());skipped=any(x==AgentStepStatus.SKIPPED for x in statuses.values())
        if not succeeded:record.status=AgentRunStatus.FAILED;record.error_code="AGENT_EXECUTION_FAILED";record.error_message="No Agent step completed successfully.";self.session.commit();return None
        summaries=[{"step_id":sid,**result.model_dump(mode="json",exclude={"rows"}),"rows":result.rows[:10],"attempt_count":item.attempt_count,"repair_count":item.repair_count} for sid,result,item in results]
        for item in self.repo.steps(record.id):
            if item.status in (AgentStepStatus.FAILED,AgentStepStatus.SKIPPED):summaries.append({"step_id":item.step_id,"status":item.status.value,"error_code":item.error_code,"error_message":item.error_message,"attempt_count":item.attempt_count,"repair_count":item.repair_count})
        try:
            final=self.provider.generate_final_summary(record.user_question,plan.summary,summaries)
            if not isinstance(final,AgentFinalResponse):final=AgentFinalResponse.model_validate(final)
            final=final.model_copy(update={"key_findings":final.key_findings[:self.settings.agent_max_final_findings],"used_tools":list(dict.fromkeys([r.tool for _,r,_ in results])),"artifacts":[AgentArtifact(type=r.artifact_type,id=r.artifact_id,step_id=sid) for sid,r,_ in results if r.artifact_type and r.artifact_id]});record.final_summary_json=final.model_dump(mode="json");record.status=AgentRunStatus.PARTIAL if failed or skipped else AgentRunStatus.SUCCEEDED;self.session.commit();return final
        except Exception:record.status=AgentRunStatus.PARTIAL;record.error_code="AGENT_FINAL_SYNTHESIS_FAILED";record.error_message="Final structured synthesis failed.";self.session.commit();return None
