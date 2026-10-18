"""Document current AST boundaries without claiming field-level authorization."""

import pytest

from app.config import Settings
from app.exceptions import SQLValidationError
from app.query.validator import SQLValidator


@pytest.mark.parametrize(
    "sql",
    [
        "/* harmless description */ DROP TABLE dataset",
        "DELETE /* comment between tokens */ FROM dataset",
        "SELECT * FROM dataset; /* second statement */ UPDATE dataset SET sales=0",
        "SELECT * FROM dataset; -- end of query\nINSERT INTO dataset VALUES ('X', 1)",
    ],
)
def test_comments_do_not_hide_dangerous_statements(sql):
    with pytest.raises(SQLValidationError):
        SQLValidator(Settings()).validate(sql)


def test_benign_comment_is_allowed():
    assert SQLValidator(Settings()).validate("SELECT /* readable comment */ * FROM dataset").limit == 100


def test_sql_parse_failure_is_rejected():
    with pytest.raises(SQLValidationError, match="could not be parsed"):
        SQLValidator(Settings()).validate("SELECT ( FROM dataset")


def test_oversized_sql_is_rejected_before_execution():
    with pytest.raises(SQLValidationError, match="length limit"):
        SQLValidator(Settings(query_max_sql_length=20)).validate("SELECT * FROM dataset WHERE sales > 0")


@pytest.mark.parametrize("limit", ["1 + 1", "'100'"])
def test_nonliteral_or_noninteger_limit_is_rejected(limit):
    with pytest.raises(SQLValidationError, match="positive integer literal"):
        SQLValidator(Settings()).validate(f"SELECT * FROM dataset LIMIT {limit}")


def test_unknown_column_is_not_an_ast_authorization_check():
    # Column existence is checked later by DuckDB; this validator has no schema argument.
    result = SQLValidator(Settings()).validate("SELECT not_a_real_column FROM dataset")
    assert "not_a_real_column" in result.sql
