from app.exceptions import DatasetError


class AgentError(DatasetError):
    code = "AGENT_EXECUTION_FAILED"
    status_code = 422


class AgentInvalidPlanError(AgentError):
    code = "AGENT_INVALID_PLAN"


class AgentNotFoundError(AgentError):
    code = "AGENT_RUN_NOT_FOUND"
    status_code = 404


class AgentLLMNotConfiguredError(AgentError):
    code = "AGENT_LLM_NOT_CONFIGURED"
    status_code = 503


class AgentLLMError(AgentError):
    code = "AGENT_LLM_ERROR"
    status_code = 502


class AgentTimeoutError(AgentError):
    code = "AGENT_TIMEOUT"
    status_code = 504
