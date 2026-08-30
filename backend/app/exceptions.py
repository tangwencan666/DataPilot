class DatasetError(Exception):
    status_code = 400
    code = "BAD_REQUEST"

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class InvalidFileError(DatasetError):
    status_code = 400


class FileTooLargeError(DatasetError):
    status_code = 413


class DatasetParseError(DatasetError):
    status_code = 422


class DatasetNotFoundError(DatasetError):
    status_code = 404
    code = "DATASET_NOT_FOUND"


class ProfileNotFoundError(DatasetError):
    status_code = 404
    code = "PROFILE_NOT_FOUND"


class ProfileGenerationError(DatasetError):
    status_code = 422
    code = "PROFILE_GENERATION_FAILED"


class QueryError(DatasetError):
    code = "QUERY_FAILED"


class LLMNotConfiguredError(QueryError):
    status_code = 503
    code = "LLM_NOT_CONFIGURED"


class LLMProviderError(QueryError):
    status_code = 502
    code = "SQL_GENERATION_FAILED"


class LLMInvalidResponseError(QueryError):
    status_code = 502
    code = "LLM_INVALID_RESPONSE"


class SQLValidationError(QueryError):
    status_code = 422
    code = "SQL_VALIDATION_FAILED"


class QueryExecutionError(QueryError):
    status_code = 422
    code = "QUERY_EXECUTION_FAILED"


class QueryTimeoutError(QueryError):
    status_code = 408
    code = "QUERY_TIMEOUT"


class QueryNotFoundError(QueryError):
    status_code = 404
    code = "QUERY_NOT_FOUND"
