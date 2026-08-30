from app.exceptions import DatasetError

class ChartError(DatasetError):
    code = "CHART_GENERATION_FAILED"; status_code = 422
class ChartValidationError(ChartError): code = "CHART_VALIDATION_FAILED"
class InvalidColumnError(ChartError): code = "CHART_INVALID_COLUMN"
class InvalidColumnTypeError(ChartError): code = "CHART_INVALID_COLUMN_TYPE"
class TooManySeriesError(ChartError): code = "CHART_TOO_MANY_SERIES"
class TooManyPointsError(ChartError): code = "CHART_TOO_MANY_POINTS"
class NoDataError(ChartError): code = "CHART_NO_DATA"
class OptionTooLargeError(ChartError): code = "CHART_OPTION_TOO_LARGE"
class ChartNotFoundError(ChartError): code = "CHART_NOT_FOUND"; status_code = 404
