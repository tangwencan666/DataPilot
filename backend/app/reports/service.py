import html,json,time,logging
from datetime import datetime,timezone
from app.models import AgentRunStatus,ReportStatus
from app.reports.errors import *
from app.reports.evidence import ReportEvidenceBuilder
from app.reports.schemas import *
from app.repositories import AgentRunRepository,AnalysisQueryRepository,AnalysisRunRepository,ChartRepository,DatasetProfileRepository,DatasetRepository,ReportRepository
logger=logging.getLogger(__name__)
class InsightValidator:
 def __init__(self,settings):self.s=settings
 def validate(self,result,evidence):
  result=InsightSet.model_validate(result);ids=[x.id for x in result.insights]
  if len(ids)!=len(set(ids)) or len(ids)>self.s.report_max_insights:raise ReportInvalidInsights("Insight ids must be unique and within limit.")
  allowed=set(evidence.evidence_refs)
  if any(ref not in allowed for x in result.insights for ref in x.evidence_refs):raise ReportInvalidInsights("Insight references unsupported evidence.")
  return result
class ReportService:
 def __init__(self,session,settings,provider):
  self.db=session;self.s=settings;self.provider=provider;self.datasets=DatasetRepository(session);self.runs=AgentRunRepository(session);self.reports=ReportRepository(session);self.profiles=DatasetProfileRepository(session);self.charts=ChartRepository(session);self.queries=AnalysisQueryRepository(session);self.analyses=AnalysisRunRepository(session)
 def create(self,dataset_id,run_id):
  dataset=self.datasets.get_by_id(dataset_id)
  if not dataset:raise ReportSourceNotFound("Dataset not found.")
  from app.models import AgentRun
  any_run=self.db.get(AgentRun,run_id)
  if any_run and any_run.dataset_id!=dataset_id:raise ReportDatasetMismatch("Agent Run belongs to another Dataset.")
  run=self.runs.get(dataset_id,run_id)
  if not run:raise ReportSourceNotFound("Agent Run not found.")
  if run.status not in (AgentRunStatus.SUCCEEDED,AgentRunStatus.PARTIAL):raise ReportSourceNotReady("Only SUCCEEDED or PARTIAL Agent Runs can be reported.")
  if getattr(self.provider,"is_configured",True) is False:raise ReportLLMNotConfigured("Report generation requires an LLM provider.")
  record=self.reports.create(dataset_id,run_id);record.status=ReportStatus.GENERATING;self.db.commit();started=time.perf_counter()
  try:
   ev=ReportEvidenceBuilder(self.s,self.runs,self.profiles,self.charts,self.queries,self.analyses).build(dataset,run);insights=InsightValidator(self.s).validate(self.provider.generate_insights(ev.model_dump(mode="json")),ev);draft=ReportDraft.model_validate(self.provider.compose_report(ev.model_dump(mode="json"),insights.model_dump(mode="json")))
   methods=sorted(set(x.tool for x in ev.step_evidence));arts=[ReportArtifact(type=x.type,id=x.id,title=x.title,summary=x.summary) for x in ev.artifact_evidence];sections=[ReportSection(key="objective",title="Analysis Objective",content=ev.question),ReportSection(key="dataset",title="Dataset Overview",content=f"{dataset.name}: {dataset.row_count} rows × {dataset.column_count} columns."),ReportSection(key="findings",title="Detailed Analysis",content=draft.detailed_analysis),ReportSection(key="visualizations",title="Visualizations",content="Referenced chart artifacts are listed below." if any(x.type=="chart" for x in arts) else "No visualization artifact was produced."),ReportSection(key="quality",title="Data Quality & Caveats",content=json.dumps(ev.profile_evidence,ensure_ascii=False)),ReportSection(key="methodology",title="Methodology",content=", ".join(methods)),ReportSection(key="conclusion",title="Conclusion",content=draft.conclusion)]
   doc=ReportDocument(title=draft.title,executive_summary=draft.executive_summary,sections=sections,key_insights=insights.insights,limitations=list(dict.fromkeys(ev.limitations+draft.limitations)),methodology=methods,artifacts=arts,source_status=run.status.value,generated_at=datetime.now(timezone.utc));record.title=doc.title;record.executive_summary=doc.executive_summary;record.report_json=doc.model_dump(mode="json");record.status=ReportStatus.READY;record.insight_count=len(doc.key_insights);record.artifact_count=len(arts);record.evidence_truncated=ev.evidence_truncated;record.generation_time_ms=round((time.perf_counter()-started)*1000,3);self.db.commit();self.db.refresh(record);logger.info("report_id=%s dataset_id=%s agent_run_id=%s status=READY duration_ms=%s insight_count=%s artifact_count=%s",record.id,dataset_id,run_id,record.generation_time_ms,record.insight_count,record.artifact_count);return record
  except ReportError:raise
  except Exception as exc:record.status=ReportStatus.FAILED;record.error_code="REPORT_GENERATION_FAILED";record.error_message="Report generation failed.";self.db.commit();raise ReportInvalidOutput("Report provider returned invalid structured output.") from exc
 def list(self,dataset_id,page,page_size):return self.reports.list(dataset_id,page,page_size)
 def get(self,dataset_id,report_id):
  x=self.reports.get(dataset_id,report_id)
  if not x:raise ReportNotFound("Report not found.")
  return x
 def delete(self,dataset_id,report_id):self.db.delete(self.get(dataset_id,report_id));self.db.commit()
 def export(self,dataset_id,report_id,fmt):
  doc=ReportDocument.model_validate(self.get(dataset_id,report_id).report_json)
  if fmt=="markdown":
   clean=lambda s:s.replace("<","&lt;").replace(">","&gt;");text=f"# {clean(doc.title)}\n\n## Executive Summary\n\n{clean(doc.executive_summary)}\n\n"+"\n\n".join(f"## {clean(s.title)}\n\n{clean(s.content)}" for s in doc.sections)+"\n\n## Key Insights\n\n"+"\n".join(f"- **{clean(x.title)}**: {clean(x.statement)} ({', '.join(x.evidence_refs)})" for x in doc.key_insights)+"\n\n## Limitations\n\n"+"\n".join(f"- {clean(x)}" for x in doc.limitations)
  elif fmt=="html":
   safe=lambda s:html.escape(s).replace("javascript:","").replace("onclick","on-click").replace("onerror","on-error")
   text="<!doctype html><html><body>"+f"<h1>{safe(doc.title)}</h1><h2>Executive Summary</h2><p>{safe(doc.executive_summary)}</p>"+"".join(f"<h2>{safe(s.title)}</h2><p>{safe(s.content)}</p>" for s in doc.sections)+"</body></html>"
  else:raise ReportUnsupportedFormat("Supported formats: markdown, html.")
  data=text.encode("utf-8")
  if len(data)>self.s.report_max_export_bytes:raise ReportExportTooLarge("Report export exceeds configured limit.")
  return data
def report_read(x):return ReportRead(id=x.id,dataset_id=x.dataset_id,agent_run_id=x.agent_run_id,title=x.title,status=x.status,executive_summary=x.executive_summary,report=ReportDocument.model_validate(x.report_json) if x.report_json else None,insight_count=x.insight_count,artifact_count=x.artifact_count,evidence_truncated=x.evidence_truncated,generation_time_ms=x.generation_time_ms,error_code=x.error_code,error_message=x.error_message,created_at=x.created_at,updated_at=x.updated_at)
