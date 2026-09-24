import io
import re
from pathlib import Path
from typing import Union
import duckdb
import pandas as pd

def sanitize_table_name(name: str) -> str:
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
    safe_name = sanitize_table_name(table_name)
    replace_clause = "OR REPLACE " if replace else ""

    if not file_type and isinstance(file_source, (str, Path)):
        file_type = Path(file_source).suffix.lstrip(".").lower()

    if not file_type:
        raise ValueError("file_type must be specified when passing binary streams.")

    file_type = file_type.lower()

    if file_type in ("csv", "tsv"):
        if isinstance(file_source, (str, Path)):
            file_path = str(Path(file_source).resolve())
            con.execute(
                f"CREATE {replace_clause}VIEW {safe_name} AS SELECT * FROM read_csv_auto(?)",
                [file_path],
            )
        else:
            if isinstance(file_source, bytes):
                file_source = io.BytesIO(file_source)
            sep = "\t" if file_type == "tsv" else ","
            
            # Encoding fallback sequence for special characters in CSVs
            try:
                df = pd.read_csv(file_source, sep=sep, encoding="utf-8")
            except UnicodeDecodeError:
                file_source.seek(0)
                try:
                    df = pd.read_csv(file_source, sep=sep, encoding="latin1")
                except Exception:
                    file_source.seek(0)
                    df = pd.read_csv(file_source, sep=sep, encoding="cp1252")
                
            con.register(safe_name, df)

    elif file_type in ("xlsx", "xls"):
        if isinstance(file_source, bytes):
            file_source = io.BytesIO(file_source)
        df = pd.read_excel(file_source)
        con.register(safe_name, df)

    else:
        raise ValueError(f"Unsupported file format '{file_type}'.")

    return safe_name