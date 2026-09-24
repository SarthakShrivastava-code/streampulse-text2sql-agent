"""database/schema.py: Table registry and custom file ingestion into DuckDB."""

from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Union
import duckdb
import pandas as pd


def sanitize_table_name(name: str) -> str:
    """Sanitizes an input string into a safe SQL identifier."""
    cleaned = re.sub(r"[^\w]+", "_", name.strip().lower())
    if not cleaned or cleaned[0].isdigit():
        cleaned = f"tbl_{cleaned}"
    return cleaned


def register_uploaded_file(
    con: duckdb.DuckDBPyConnection,
    file_source: Union[str, Path, io.BytesIO, bytes],
    table_name: str,
    file_type: str | None = None,
    replace: bool = True,
) -> str:
    """Registers an uploaded CSV or Excel file as a view/table in DuckDB.

    Args:
        con: Active DuckDB connection.
        file_source: File path, Path object, raw bytes, or BytesIO stream.
        table_name: Desired name for the registered table/view.
        file_type: 'csv', 'tsv', 'xlsx', or 'xls'. Inferred from path if omitted.
        replace: If True, replaces any existing table/view with the same name.

    Returns:
        The sanitized table name registered in DuckDB.
    """
    safe_name = sanitize_table_name(table_name)
    replace_clause = "OR REPLACE " if replace else ""

    # Determine file extension if not explicitly supplied
    if not file_type and isinstance(file_source, (str, Path)):
        file_type = Path(file_source).suffix.lstrip(".").lower()

    if not file_type:
        raise ValueError("file_type must be specified when passing binary streams.")

    file_type = file_type.lower()

    if file_type in ("csv", "tsv"):
        if isinstance(file_source, (str, Path)):
            file_path = str(Path(file_source).resolve())
            con.execute(
                f"CREATE {replace_clause}VIEW {safe_name} AS "
                f"SELECT * FROM read_csv_auto(?)",
                [file_path],
            )
        else:
            # Handle in-memory bytes/buffer via Pandas to avoid temp files
            if isinstance(file_source, bytes):
                file_source = io.BytesIO(file_source)
            sep = "\t" if file_type == "tsv" else ","
            df = pd.read_csv(file_source, sep=sep)
            con.register(safe_name, df)

    elif file_type in ("xlsx", "xls"):
        # Load Excel via pandas DataFrame and register directly in DuckDB
        if isinstance(file_source, bytes):
            file_source = io.BytesIO(file_source)
        df = pd.read_excel(file_source)
        con.register(safe_name, df)

    else:
        raise ValueError(
            f"Unsupported file format '{file_type}'. Supported formats: csv, tsv, xlsx, xls."
        )

    return safe_name