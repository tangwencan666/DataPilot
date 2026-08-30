from dataclasses import dataclass
from io import BytesIO
from typing import Any
from zipfile import BadZipFile

import pandas as pd

from app.exceptions import DatasetParseError


@dataclass
class ParsedDataset:
    row_count: int
    column_count: int
    columns: list[dict[str, Any]]
    preview_rows: list[dict[str, Any]]
    metadata: dict[str, Any]


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    object_frame = frame.astype(object)
    return object_frame.where(pd.notna(object_frame), None).to_dict(orient="records")


def _result(frame: pd.DataFrame, preview_limit: int, metadata: dict[str, Any]) -> ParsedDataset:
    columns = [
        {
            "name": str(column),
            "dtype": str(frame[column].dtype),
            "missing": int(frame[column].isna().sum()),
            "unique": int(frame[column].nunique(dropna=True)),
        }
        for column in frame.columns
    ]
    return ParsedDataset(len(frame), len(frame.columns), columns, _records(frame.head(preview_limit)), {**metadata, "columns": columns})


def parse_dataset(content: bytes, file_type: str, preview_limit: int) -> ParsedDataset:
    frame, metadata = load_dataframe(content, file_type)
    return _result(frame, preview_limit, metadata)


def load_dataframe(content: bytes, file_type: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    try:
        if file_type == "csv":
            return pd.read_csv(BytesIO(content)), {"encoding": "utf-8"}
        if file_type == "xlsx":
            workbook = pd.ExcelFile(BytesIO(content), engine="openpyxl")
            selected_sheet = workbook.sheet_names[0]
            return workbook.parse(selected_sheet), {"sheet_names": workbook.sheet_names, "selected_sheet": selected_sheet}
    except (UnicodeDecodeError, pd.errors.ParserError, ValueError, OSError, TypeError, KeyError, BadZipFile) as exc:
        raise DatasetParseError(f"无法解析 {file_type.upper()} 文件") from exc
    raise DatasetParseError("不支持的文件类型")
