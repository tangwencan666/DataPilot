import pytest
from app.agents.observation import FailureClassifier,RetryPolicy,observe
from app.agents.schemas import FailureCategory,ToolExecutionResult,ToolName
from app.config import Settings

@pytest.mark.parametrize("code,category",[
 ("ANALYSIS_INVALID_COLUMN",FailureCategory.INVALID_COLUMN),("CHART_INVALID_COLUMN_TYPE",FailureCategory.INVALID_TYPE),("INVALID_AGGREGATION",FailureCategory.INVALID_AGGREGATION),("SQL_SYNTAX_ERROR",FailureCategory.SQL_SYNTAX_ERROR),("SQL_VALIDATION_ERROR",FailureCategory.SQL_VALIDATION_ERROR),("ANALYSIS_TIMEOUT",FailureCategory.TIMEOUT),("ANALYSIS_DATASET_TOO_LARGE",FailureCategory.RESOURCE_LIMIT),("LLM_AUTH_ERROR",FailureCategory.LLM_ERROR),("CHART_NOT_FOUND",FailureCategory.NOT_FOUND),("UNSUPPORTED",FailureCategory.UNSUPPORTED),("AGENT_TOOL_FAILED",FailureCategory.INTERNAL_ERROR),("SQL_FORBIDDEN_FUNCTION",FailureCategory.SECURITY_REJECTION)])
def test_failure_classification(code,category):assert FailureClassifier().classify(code)==category
@pytest.mark.parametrize("category",[FailureCategory.INVALID_COLUMN,FailureCategory.INVALID_TYPE,FailureCategory.INVALID_AGGREGATION,FailureCategory.SQL_SYNTAX_ERROR,FailureCategory.SQL_VALIDATION_ERROR,FailureCategory.EMPTY_RESULT,FailureCategory.VALIDATION_ERROR])
def test_retryable_categories(category):assert RetryPolicy().allows(category,0,0,Settings())
@pytest.mark.parametrize("category",[FailureCategory.TIMEOUT,FailureCategory.RESOURCE_LIMIT,FailureCategory.LLM_ERROR,FailureCategory.INTERNAL_ERROR,FailureCategory.NOT_FOUND,FailureCategory.SECURITY_REJECTION])
def test_non_retryable_categories(category):assert not RetryPolicy().allows(category,0,0,Settings())
def test_retry_budgets_enforced():
    settings=Settings(agent_max_repairs_per_step=1,agent_max_repairs_per_run=1);assert not RetryPolicy().allows(FailureCategory.INVALID_COLUMN,1,0,settings);assert not RetryPolicy().allows(FailureCategory.INVALID_COLUMN,0,1,settings)
def test_success_observation_accepted():
    result=ToolExecutionResult(tool=ToolName.SQL,status="SUCCEEDED",summary="ok",columns=["x"],rows=[[1]],row_count=1);obs=observe("s",ToolName.SQL,result,None,None,Settings(),0,0);assert obs.success and not obs.retryable
def test_empty_result_observed_as_retryable():
    result=ToolExecutionResult(tool=ToolName.SQL,status="SUCCEEDED",summary="empty",row_count=0);obs=observe("s",ToolName.SQL,result,None,None,Settings(),0,0);assert obs.error_category==FailureCategory.EMPTY_RESULT and obs.retryable
