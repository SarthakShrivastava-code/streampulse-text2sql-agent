"""database/security.py: Query parsing and SQL injection/write prevention."""

from __future__ import annotations

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError


class SQLSecurityViolation(Exception):
    """Raised when a query fails security constraints."""


# Expressions that indicate non-read-only or state-altering behavior
DISALLOWED_ROOT_EXPRESSIONS = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Create,
    exp.Drop,
    exp.Alter,
    exp.Command,
    exp.Pragma,
)


def validate_read_only_query(sql: str, dialect: str = "duckdb") -> None:
    """Validates that a SQL query contains strictly one read-only SELECT statement.

    Args:
        sql: Raw SQL query string.
        dialect: SQL dialect name (defaults to 'duckdb').

    Raises:
        SQLSecurityViolation: If multiple statements, non-SELECT root operations,
            or modification expressions are detected.
        ValueError: If query is empty or cannot be parsed.
    """
    if not sql or not sql.strip():
        raise ValueError("Query string cannot be empty.")

    try:
        # sqlglot.parse returns a list of all parsed AST statements
        statements = sqlglot.parse(sql, read=dialect)
    except ParseError as exc:
        raise ValueError(f"SQL parsing error: {exc}") from exc

    # Filter out empty statements (e.g., trailing semicolons)
    parsed_statements = [stmt for stmt in statements if stmt is not None]

    if not parsed_statements:
        raise ValueError("No executable SQL statements found.")

    # 1. Block multi-statement execution
    if len(parsed_statements) > 1:
        raise SQLSecurityViolation(
            f"Multi-statement queries are forbidden. Found {len(parsed_statements)} statements."
        )

    stmt = parsed_statements[0]

    # 2. Enforce top-level SELECT or UNION-like construct
    if not isinstance(stmt, (exp.Select, exp.Union)):
        raise SQLSecurityViolation(
            f"Unauthorized statement type '{stmt.key.upper()}'. Only SELECT queries are permitted."
        )

    # 3. Deep-walk AST to detect embedded DML/DDL or side-effect operations (e.g., INTO OUTFILE, COPY)
    for node in stmt.walk():
        if isinstance(node, DISALLOWED_ROOT_EXPRESSIONS):
            raise SQLSecurityViolation(
                f"Disallowed expression detected inside statement: {node.key.upper()}"
            )
        # Prevent export operations like `COPY ... TO 'file.csv'`
        if isinstance(node, exp.Copy):
            raise SQLSecurityViolation("COPY operations are not permitted.")
        # Prevent SELECT ... INTO operations
        if isinstance(node, exp.Into):
            raise SQLSecurityViolation("SELECT INTO operations are not permitted.")