from dataclasses import dataclass

from sqlglot import exp, parse
from sqlglot.errors import ParseError

from app.config import Settings
from app.exceptions import SQLValidationError

DANGEROUS_FUNCTIONS = {
    "read_csv",
    "read_csv_auto",
    "read_parquet",
    "read_json",
    "read_json_auto",
    "read_text",
    "glob",
    "sqlite_scan",
    "sqlite_attach",
    "postgres_scan",
    "postgres_attach",
    "http_get",
    "httpfs",
}
SYSTEM_NAMES = {"information_schema", "sqlite_master", "pg_catalog", "duckdb_tables", "duckdb_columns"}
FORBIDDEN_NODES = tuple(
    node
    for name in ("Insert", "Update", "Delete", "Drop", "Alter", "Create", "Copy", "Attach", "Detach", "Pragma", "Command", "Merge")
    if (node := getattr(exp, name, None)) is not None
)


@dataclass
class ValidatedSQL:
    sql: str
    execution_sql: str
    limit: int


class SQLValidator:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def validate(self, sql: str) -> ValidatedSQL:
        if not sql or len(sql) > self.settings.query_max_sql_length:
            raise SQLValidationError("Generated SQL is empty or exceeds the configured length limit.")
        try:
            statements = [statement for statement in parse(sql, read="duckdb") if statement is not None]
        except ParseError as exc:
            raise SQLValidationError("Generated SQL could not be parsed.") from exc
        if len(statements) != 1:
            raise SQLValidationError("Exactly one SQL statement is allowed.")
        statement = statements[0]
        if not isinstance(statement, exp.Query) or isinstance(statement, FORBIDDEN_NODES):
            raise SQLValidationError("Only SELECT queries are allowed.")
        if any(isinstance(node, FORBIDDEN_NODES) for node in statement.walk()):
            raise SQLValidationError("SQL contains a prohibited operation.")

        cte_names = {cte.alias_or_name.lower() for cte in statement.find_all(exp.CTE)}
        dataset_seen = False
        for table in statement.find_all(exp.Table):
            name = table.name.lower()
            catalog = (table.catalog or "").lower()
            db = (table.db or "").lower()
            if name in SYSTEM_NAMES or catalog in SYSTEM_NAMES or db in SYSTEM_NAMES:
                raise SQLValidationError("System catalogs are not accessible.")
            if name != "dataset" and name not in cte_names:
                raise SQLValidationError(f"Query may only access the dataset table, not '{name or 'external source'}'.")
            if name == "dataset":
                dataset_seen = True
        if not dataset_seen:
            raise SQLValidationError("Query must read from the dataset table.")

        for function in statement.find_all(exp.Func):
            function_name = function.sql_name().lower()
            if isinstance(function, exp.Anonymous):
                function_name = function.name.lower()
            if function_name in DANGEROUS_FUNCTIONS or any(
                token in function_name for token in ("scan", "attach", "read_csv", "read_parquet", "read_json", "http")
            ):
                raise SQLValidationError(f"Function '{function_name}' is prohibited.")
        sql_lower = statement.sql(dialect="duckdb").lower()
        if any(name in sql_lower for name in SYSTEM_NAMES):
            raise SQLValidationError("System catalogs are not accessible.")

        limit_node = statement.args.get("limit")
        if limit_node is None:
            limit = self.settings.query_default_limit
        else:
            expression = limit_node.expression
            if not isinstance(expression, exp.Literal) or not expression.is_int:
                raise SQLValidationError("LIMIT must be a positive integer literal.")
            limit = max(1, min(int(expression.this), self.settings.query_max_limit))
        display = statement.copy().limit(limit).sql(dialect="duckdb")
        execution = statement.copy().limit(limit + 1).sql(dialect="duckdb")
        return ValidatedSQL(sql=display, execution_sql=execution, limit=limit)
