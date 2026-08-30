from pathlib import Path

import openpyxl
import pytest

from app.config import Settings
from app.exceptions import QueryExecutionError, QueryTimeoutError
from app.query.executor import DuckDBQueryExecutor
from app.query.validator import SQLValidator


def settings() -> Settings:
    return Settings(database_url="sqlite://", query_default_limit=2, query_max_limit=3, query_max_result_cells=100)


def test_csv_aggregation_nulls_limits_and_serialization(tmp_path: Path) -> None:
    path = tmp_path / "data.csv"; path.write_text("city,sales,day\nA,10,2024-01-01\nA,20,2024-01-02\nB,,2024-01-03\nB,5,2024-01-04\n", encoding="utf-8")
    validator = SQLValidator(settings()); executor = DuckDBQueryExecutor(settings())
    result = executor.execute(path, "csv", validator.validate("SELECT city, SUM(sales) total FROM dataset GROUP BY city ORDER BY city"))
    assert result.columns == ["city", "total"]
    assert result.rows == [["A", 30.0], ["B", 5.0]]
    assert result.execution_time_ms >= 0
    dates = executor.execute(path, "csv", validator.validate("SELECT CAST(day AS DATE) day FROM dataset ORDER BY day LIMIT 3"))
    assert dates.rows[0][0] == "2024-01-01T00:00:00"
    assert dates.truncated


def test_xlsx_query(tmp_path: Path) -> None:
    path = tmp_path / "data.xlsx"; workbook = openpyxl.Workbook(); sheet = workbook.active
    sheet.append(["category", "amount"]); sheet.append(["A", 2]); sheet.append(["B", 3]); workbook.save(path)
    result = DuckDBQueryExecutor(settings()).execute(path, "xlsx", SQLValidator(settings()).validate("SELECT SUM(amount) total FROM dataset"))
    assert result.rows == [[5.0]]


def test_invalid_column_is_safe_error(tmp_path: Path) -> None:
    path = tmp_path / "data.csv"; path.write_text("a\n1\n", encoding="utf-8")
    with pytest.raises(QueryExecutionError):
        DuckDBQueryExecutor(settings()).execute(path, "csv", SQLValidator(settings()).validate("SELECT missing FROM dataset"))


def test_timeout_interrupt_mechanism(tmp_path: Path, monkeypatch) -> None:
    from concurrent.futures import TimeoutError as FutureTimeout
    import app.query.executor as executor_module

    class TimeoutFuture:
        def result(self, timeout=None): raise FutureTimeout()
    class TimeoutPool:
        def __init__(self, **kwargs): pass
        def submit(self, *args): return TimeoutFuture()
        def shutdown(self, **kwargs): pass

    monkeypatch.setattr(executor_module, "ThreadPoolExecutor", TimeoutPool)
    path = tmp_path / "data.csv"; path.write_text("a\n1\n", encoding="utf-8")
    with pytest.raises(QueryTimeoutError):
        DuckDBQueryExecutor(settings()).execute(path, "csv", SQLValidator(settings()).validate("SELECT * FROM dataset"))


def test_max_result_cells_truncates(tmp_path: Path) -> None:
    path = tmp_path / "data.csv"; path.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")
    limited = Settings(database_url="sqlite://", query_default_limit=10, query_max_limit=10, query_max_result_cells=2)
    result = DuckDBQueryExecutor(limited).execute(path, "csv", SQLValidator(limited).validate("SELECT * FROM dataset"))
    assert result.row_count == 1
    assert result.truncated
