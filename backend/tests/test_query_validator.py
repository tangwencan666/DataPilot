import pytest

from app.config import Settings
from app.exceptions import SQLValidationError
from app.query.validator import SQLValidator


@pytest.fixture
def validator() -> SQLValidator:
    return SQLValidator(Settings(database_url="sqlite://", query_default_limit=25, query_max_limit=100))


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM dataset",
        "SELECT city FROM dataset WHERE sales > 10",
        "SELECT city, SUM(sales) FROM dataset GROUP BY city ORDER BY 2 DESC LIMIT 10",
        "WITH totals AS (SELECT city, SUM(sales) total FROM dataset GROUP BY city) SELECT * FROM totals",
    ],
)
def test_allows_safe_queries(validator: SQLValidator, sql: str) -> None:
    assert validator.validate(sql).sql.startswith(("SELECT", "WITH"))


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE dataset",
        "DELETE FROM dataset",
        "UPDATE dataset SET x=1",
        "INSERT INTO dataset VALUES (1)",
        "CREATE TABLE x(a int)",
        "ALTER TABLE dataset ADD x int",
        "ATTACH 'x.db' AS x",
        "COPY dataset TO 'x.csv'",
        "PRAGMA version",
        "INSTALL httpfs",
        "LOAD httpfs",
        "SELECT 1; SELECT 2",
        "SELECT * FROM information_schema.tables",
        "SELECT * FROM sqlite_master",
        "SELECT * FROM other",
        "SELECT * FROM read_csv_auto('secret.csv')",
        "SELECT * FROM read_parquet('secret.parquet')",
        "SELECT * FROM read_json('https://evil.test/x')",
        "SeLeCt * FrOm read_csv('x')",
        "SELECT * FROM dataset; -- safe\nDROP TABLE dataset",
        "SELECT * FROM postgres_scan('x', 'y', 'z')",
        "SELECT * FROM sqlite_scan('x', 'y')",
        "SELECT * FROM glob('*')",
        "CALL test()",
        "DETACH database x",
        "EXPORT DATABASE 'x'",
        "IMPORT DATABASE 'x'",
        "VACUUM",
        "SELECT 1",
    ],
)
def test_rejects_unsafe_queries(validator: SQLValidator, sql: str) -> None:
    with pytest.raises(SQLValidationError):
        validator.validate(sql)


def test_enforces_default_and_max_limit(validator: SQLValidator) -> None:
    assert validator.validate("SELECT * FROM dataset").limit == 25
    limited = validator.validate("SELECT * FROM dataset LIMIT 999999")
    assert limited.limit == 100
    assert "LIMIT 100" in limited.sql
