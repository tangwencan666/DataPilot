from app.exceptions import DatasetError


class ReportError(DatasetError):
    code = "REPORT_GENERATION_FAILED"
    status_code = 422


class ReportSourceNotFound(ReportError):
    code = "REPORT_SOURCE_NOT_FOUND"
    status_code = 404


class ReportSourceNotReady(ReportError):
    code = "REPORT_SOURCE_NOT_READY"


class ReportDatasetMismatch(ReportError):
    code = "REPORT_DATASET_MISMATCH"


class ReportNotFound(ReportError):
    code = "REPORT_NOT_FOUND"
    status_code = 404


class ReportLLMNotConfigured(ReportError):
    code = "REPORT_LLM_NOT_CONFIGURED"
    status_code = 503


class ReportInvalidInsights(ReportError):
    code = "REPORT_INVALID_INSIGHTS"


class ReportInvalidOutput(ReportError):
    code = "REPORT_INVALID_OUTPUT"


class ReportExportTooLarge(ReportError):
    code = "REPORT_EXPORT_TOO_LARGE"


class ReportUnsupportedFormat(ReportError):
    code = "REPORT_UNSUPPORTED_FORMAT"
