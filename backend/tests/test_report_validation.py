import pytest
from pydantic import ValidationError
from app.config import Settings
from app.reports.errors import ReportInvalidInsights
from app.reports.schemas import Insight,InsightSet,ReportEvidence,ReportDraft
from app.reports.service import InsightValidator
def evidence(refs=None):return ReportEvidence(dataset_summary={},question="q",goal="g",planner_summary="p",execution_summary={},step_evidence=[],profile_evidence={},artifact_evidence=[],final_synthesis={},limitations=[],evidence_refs=refs or ["step:s1"])
def insight(id="i1",refs=None):return {"id":id,"title":"Finding","statement":"Evidence-backed statement","importance":"HIGH","confidence":.8,"evidence_refs":refs or ["step:s1"],"limitations":[]}
def test_valid_insight():assert InsightValidator(Settings()).validate({"insights":[insight()]},evidence()).insights[0].confidence==.8
def test_duplicate_id_rejected():
 with pytest.raises(ReportInvalidInsights):InsightValidator(Settings()).validate({"insights":[insight(),insight()]},evidence())
def test_missing_evidence_ref_rejected():
 with pytest.raises(ReportInvalidInsights):InsightValidator(Settings()).validate({"insights":[insight(refs=["chart:fake"])]},evidence())
def test_too_many_insights():
 with pytest.raises(ReportInvalidInsights):InsightValidator(Settings(report_max_insights=1)).validate({"insights":[insight("a"),insight("b")]},evidence())
@pytest.mark.parametrize("field,value",[("confidence",-1),("confidence",2),("importance","CRITICAL"),("title",""),("statement",""),("evidence_refs",[]),("title","x"*201),("statement","x"*2001),("evidence_refs",[f"step:{i}" for i in range(21)]),("limitations",["x"]*11),("id","bad id"),("confidence",None)])
def test_invalid_insight_schema(field,value):
 data=insight();data[field]=value
 with pytest.raises(ValidationError):Insight.model_validate(data)
@pytest.mark.parametrize("payload",[{"title":"","executive_summary":"x","detailed_analysis":"x","conclusion":"x"},{"title":"x","executive_summary":"","detailed_analysis":"x","conclusion":"x"},{"title":"x"*201,"executive_summary":"x","detailed_analysis":"x","conclusion":"x"},{"title":"x","executive_summary":"x","detailed_analysis":"","conclusion":"x"}])
def test_invalid_report_draft(payload):
 with pytest.raises(ValidationError):ReportDraft.model_validate(payload)
