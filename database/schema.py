import duckdb


_SAMPLE_SALES = [
    ("Electronics", "Laptop", 3, 2700.00),
    ("Electronics", "Headphones", 8, 1200.00),
    ("Home", "Desk Lamp", 12, 480.00),
    ("Home", "Office Chair", 4, 1000.00),
    ("Outdoor", "Tent", 2, 700.00),
]

_SCHEMA_INFO = """
Table: sales
Columns:
- category (VARCHAR): Product category
- product (VARCHAR): Product name
- quantity (INTEGER): Units sold
- total_sales (DOUBLE): Total sales amount in USD
""".strip()


def get_database_connection() -> duckdb.DuckDBPyConnection:
    connection = duckdb.connect(database=":memory:")
    connection.execute(
        """
        CREATE TABLE sales (
            category VARCHAR,
            product VARCHAR,
            quantity INTEGER,
            total_sales DOUBLE
        )
        """
    )
    connection.executemany(
        "INSERT INTO sales VALUES (?, ?, ?, ?)",
        _SAMPLE_SALES,
    )
    return connection


def get_schema_info() -> str:
    return _SCHEMA_INFO
