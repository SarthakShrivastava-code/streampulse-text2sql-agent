import pytest

from app.llm_agent import _extract_sql


def test_extract_sql_from_refusal_text_raises_value_error():
    with pytest.raises(ValueError, match="refused|rephrase|non-SQL|SELECT"):
        _extract_sql("I’m sorry, but I can’t help with that.")


def test_extract_sql_from_sql_fence_returns_query():
    raw = "```sql\nSELECT * FROM products;\n```"
    assert _extract_sql(raw) == "SELECT * FROM products;"
