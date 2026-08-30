from app.agents.context import AgentContextBuilder
from app.config import Settings
from app.models import Dataset,DatasetProfile,ProfileStatus

def dataset():return Dataset(name="sales",original_filename="sales.csv",stored_filename="secret.csv",file_type="csv",file_size=10,row_count=10,column_count=2,metadata_json={})
def profile():return DatasetProfile(dataset_id="d",status=ProfileStatus.READY,quality_score=90,profile_json={"columns":[{"name":"region","physical_dtype":"object","semantic_type":"CATEGORICAL","missing_ratio":0,"unique_count":5,"sample_values":["N","S","E","W"],"categorical":{"top_values":[1,2,3,4]}},{"name":"sales","physical_dtype":"int64","semantic_type":"NUMERIC","missing_ratio":0,"unique_count":10,"sample_values":[1,2,3,4],"numeric":{"min":1,"max":10,"mean":5}}],"issues":[{"code":str(i)} for i in range(5)],"correlations":[{"column_a":"a","column_b":"b","correlation":.5} for _ in range(4)]})
def test_context_contains_bounded_profile_and_tools():
    result=AgentContextBuilder(Settings(agent_max_sample_values=2)).build(dataset(),profile());assert result.payload["profile"]["columns"][0]["sample_values"]==["N","S"];assert set(result.payload["tools"])=={"SQL","ANALYSIS","CHART"}
def test_context_never_contains_paths_or_secrets():
    result=AgentContextBuilder(Settings()).build(dataset(),profile());text=str(result.payload);assert "secret.csv" not in text and "DATABASE_URL" not in text and "API" not in text
def test_context_deterministic_truncation():
    result=AgentContextBuilder(Settings(agent_max_context_columns=1,agent_max_quality_issues=1,agent_max_correlations=1)).build(dataset(),profile());assert result.metadata["context_truncated"] is True;assert result.metadata["included_columns"]==1
def test_context_without_profile():
    result=AgentContextBuilder(Settings()).build(dataset(),None);assert "profile" not in result.payload
