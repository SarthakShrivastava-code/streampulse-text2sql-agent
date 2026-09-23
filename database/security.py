import sqlglot
from sqlglot import exp


def is_sql_safe(sql_query: str) -> tuple[bool, str]:
    if not sql_query.strip():
        return False, "Generated SQL is empty."

    try:
        statements = sqlglot.parse(sql_query, read="duckdb")
    except sqlglot.errors.ParseError as error:
        return False, f"Invalid SQL: {error}"

    if len(statements) != 1 or not isinstance(statements[0], exp.Query):
        return False, "Only one SELECT query is allowed."

    return True, "SQL query passed security validation."
