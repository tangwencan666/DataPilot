class DatasetError(Exception):
    status_code = 400

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
