from app.exceptions import DatasetError


class AnalysisError(DatasetError):
    status_code = 422
    code = "ANALYSIS_EXECUTION_FAILED"


class AnalysisValidationError(AnalysisError):
    code = "ANALYSIS_VALIDATION_FAILED"


class AnalysisInvalidColumnError(AnalysisError):
    code = "ANALYSIS_INVALID_COLUMN"


class AnalysisUnsupportedOperationError(AnalysisError):
    code = "ANALYSIS_UNSUPPORTED_OPERATION"


class AnalysisDatasetTooLargeError(AnalysisError):
    status_code = 413
    code = "ANALYSIS_DATASET_TOO_LARGE"


class AnalysisTimeoutError(AnalysisError):
    status_code = 408
    code = "ANALYSIS_TIMEOUT"


class AnalysisResultTooLargeError(AnalysisError):
    code = "ANALYSIS_RESULT_TOO_LARGE"


class AnalysisNotFoundError(AnalysisError):
    status_code = 404
    code = "ANALYSIS_NOT_FOUND"
