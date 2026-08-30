import math
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd

from app.config import Settings
from app.exceptions import QueryExecutionError, QueryTimeoutError
from app.parsers import load_dataframe
from app.query.schemas import QueryResult
from app.query.validator import ValidatedSQL


def json_value(value: Any) -> Any:
    if value is None or value is pd.NA:
        return None
    if isinstance(value, (datetime, date, pd.Timestamp, np.datetime64)):
        return pd.Timestamp(value).isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


class DuckDBQueryExecutor:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def execute(self, path: Path, file_type: str, validated: ValidatedSQL) -> QueryResult:
        connection = duckdb.connect(database=":memory:")
        try:
            if file_type == "csv":
                connection.read_csv(str(path), header=True).create_view("dataset")
            elif file_type == "xlsx":
                frame, _ = load_dataframe(path.read_bytes(), "xlsx")
                connection.register("dataset", frame)
            else:
                raise QueryExecutionError("Unsupported managed dataset type.")
            started = time.perf_counter()
            worker = ThreadPoolExecutor(max_workers=1)
            future = worker.submit(connection.execute, validated.execution_sql)
            try:
                cursor = future.result(timeout=self.settings.query_timeout_seconds)
            except FutureTimeout as exc:
                connection.interrupt()
                worker.shutdown(wait=False, cancel_futures=True)
                raise QueryTimeoutError("Query exceeded the configured execution timeout.") from exc
            columns = [item[0] for item in cursor.description]
            cell_row_limit = max(1, self.settings.query_max_result_cells // max(1, len(columns)))
            effective_limit = min(validated.limit, cell_row_limit)
            raw_rows = cursor.fetchmany(effective_limit + 1)
            worker.shutdown(wait=True)
            elapsed = round((time.perf_counter() - started) * 1000, 3)
            truncated = len(raw_rows) > effective_limit
            rows = [[json_value(value) for value in row] for row in raw_rows[:effective_limit]]
            return QueryResult(columns=columns, rows=rows, row_count=len(rows), truncated=truncated, execution_time_ms=elapsed, sql=validated.sql)
        except QueryTimeoutError:
            raise
        except Exception as exc:
            raise QueryExecutionError("Safe query execution failed.") from exc
        finally:
            try:
                connection.close()
            except Exception:
                pass
