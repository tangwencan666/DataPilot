from app.agents.schemas import FailureCategory, ToolExecutionResult, ToolName, ToolObservation
from app.config import Settings

SECURITY_MARKERS = ("SECURITY", "FORBIDDEN", "UNSAFE", "EXTERNAL_TABLE", "DISALLOWED", "MULTIPLE_STATEMENTS")


class FailureClassifier:
    def classify(self, code: str | None, message: str = "") -> FailureCategory:
        code = (code or "").upper()
        text = f"{code} {message}".upper()
        if any(x in text for x in SECURITY_MARKERS):
            return FailureCategory.SECURITY_REJECTION
        if "NOT_FOUND" in code or code in {"DATASET_NOT_FOUND", "CHART_NOT_FOUND"}:
            return FailureCategory.NOT_FOUND
        if "TIMEOUT" in code or "TIMED_OUT" in code:
            return FailureCategory.TIMEOUT
        if "TOO_LARGE" in code or "LIMIT" in code or "TOO_MANY" in code:
            return FailureCategory.RESOURCE_LIMIT
        if "INVALID_COLUMN_TYPE" in code or "INVALID_TYPE" in code:
            return FailureCategory.INVALID_TYPE
        if "INVALID_COLUMN" in code:
            return FailureCategory.INVALID_COLUMN
        if "AGGREGATION" in code:
            return FailureCategory.INVALID_AGGREGATION
        if "SQL" in code and "SYNTAX" in text:
            return FailureCategory.SQL_SYNTAX_ERROR
        if "SQL" in code and "VALID" in text:
            return FailureCategory.SQL_VALIDATION_ERROR
        if "VALIDATION" in code or "INVALID_PLAN" in code:
            return FailureCategory.VALIDATION_ERROR
        if "LLM" in code:
            return FailureCategory.LLM_ERROR
        if "UNSUPPORTED" in code:
            return FailureCategory.UNSUPPORTED
        return FailureCategory.INTERNAL_ERROR


class RetryPolicy:
    RETRYABLE = {
        FailureCategory.INVALID_COLUMN,
        FailureCategory.INVALID_TYPE,
        FailureCategory.INVALID_AGGREGATION,
        FailureCategory.SQL_SYNTAX_ERROR,
        FailureCategory.SQL_VALIDATION_ERROR,
        FailureCategory.EMPTY_RESULT,
        FailureCategory.VALIDATION_ERROR,
    }

    def allows(self, category: FailureCategory, step_repairs: int, run_repairs: int, settings: Settings) -> bool:
        return (
            category in self.RETRYABLE
            and step_repairs < settings.agent_max_repairs_per_step
            and run_repairs < settings.agent_max_repairs_per_run
        )


def observe(
    step_id: str,
    tool: ToolName,
    result: ToolExecutionResult | None,
    error_code: str | None,
    error_message: str | None,
    settings: Settings,
    step_repairs: int,
    run_repairs: int,
) -> ToolObservation:
    if result is not None:
        category = FailureCategory.EMPTY_RESULT if result.row_count == 0 and result.artifact_id is None else FailureCategory.NONE
        success = category == FailureCategory.NONE
        message = None
        status = "SUCCEEDED" if success else "FAILED"
        summary = result.summary[: settings.agent_max_observation_chars]
    else:
        category = FailureClassifier().classify(error_code, error_message or "")
        success = False
        message = (error_message or "Tool execution failed.")[:500]
        status = "FAILED"
        summary = ""
    retryable = RetryPolicy().allows(category, step_repairs, run_repairs, settings)
    return ToolObservation(
        step_id=step_id,
        tool=tool,
        status=status,
        success=success,
        error_code=error_code,
        error_category=category,
        error_message=message,
        result_summary=summary,
        row_count=result.row_count if result else 0,
        truncated=result.truncated if result else False,
        warnings=(result.warnings[:10] if result else []),
        artifact_id=result.artifact_id if result else None,
        retryable=retryable,
    )
