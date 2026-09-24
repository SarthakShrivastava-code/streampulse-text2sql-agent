import os
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Active model verified directly from your Groq key
MODEL_NAME = "openai/gpt-oss-20b"

def get_groq_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is missing from environment variables or .env file.")
    return Groq(api_key=api_key)

def _chat_completion(messages, temperature=0.1):
    client = get_groq_client()
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=temperature
    )
    return response.choices[0].message.content.strip()

def generate_sql(user_question: str, schema_info: str) -> str:
    """Generates DuckDB SQL from natural language input."""
    system_prompt = f"""
    You are an expert SQL translation agent. Translate user questions into valid DuckDB SQL queries.
    
    Database Schema:
    {schema_info}
    
    Rules:
    1. Output ONLY executable SQL inside markdown code blocks like ```sql ... ```. No extra commentary.
    2. Only write SELECT queries. Never write DROP, DELETE, INSERT, or UPDATE statements.
    3. Match table and column names exactly as defined in the schema.
    """
    
    raw_content = _chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_question}
        ],
        temperature=0.1
    )
    return _extract_sql(raw_content)

def auto_heal_sql(user_question: str, schema_info: str, broken_sql: str, error_message: str) -> str:
    """Agentic Self-Healing Loop: Passes DuckDB execution error traceback back to Groq to fix SQL."""
    system_prompt = f"""
    You are a SQL repair agent. The previous SQL query you generated failed to execute.
    
    Database Schema:
    {schema_info}
    
    Original Question: {user_question}
    Failed SQL Query: {broken_sql}
    Execution Error: {error_message}
    
    Instructions:
    Analyze the error and return ONLY a corrected, valid DuckDB SQL query inside markdown code blocks ```sql ... ```.
    """
    
    raw_content = _chat_completion(
        messages=[{"role": "system", "content": system_prompt}],
        temperature=0.1
    )
    return _extract_sql(raw_content)

def generate_executive_summary(user_question: str, df_data_sample: str) -> str:
    """Generates a 2-sentence executive summary based on query results."""
    system_prompt = "You are a senior data analyst. Provide a concise, professional 2-sentence business summary of the query results."
    user_prompt = f"User Question: {user_question}\nData Sample:\n{df_data_sample}"
    
    return _chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.3
    )

def _extract_sql(raw_content: str) -> str:
    """Extract SQL from model output, rejecting refusal text and other non-SQL content."""
    if raw_content is None:
        raise ValueError("The model returned empty output.")

    content = raw_content.strip()
    if not content:
        raise ValueError("The model returned empty output.")

    normalized = re.sub(r"\s+", " ", content).lower()
    refusal_patterns = (
        "i'm sorry",
        "i am sorry",
        "i can’t help",
        "i can't help",
        "i can not help",
        "cannot help",
        "can't assist",
        "cannot assist",
        "not able to help",
        "as an ai",
        "i'm not able",
    )
    if any(pattern in normalized for pattern in refusal_patterns):
        raise ValueError(
            "The model refused to generate SQL for this request. Please rephrase the question or ask for a different table/metric."
        )

    if "```sql" in content:
        extracted = content.split("```sql")[1].split("```")[0].strip()
    elif "```" in content:
        extracted = content.split("```")[1].split("```")[0].strip()
    else:
        extracted = content.strip("`").strip()

    if not extracted:
        raise ValueError("The model returned no SQL query.")

    sql_tokens = [token for token in ("select", "with", "from", "show") if token in re.sub(r"\s+", " ", extracted).lower()]
    if not sql_tokens:
        raise ValueError(
            "The model returned non-SQL text instead of a SELECT query. Please rephrase your question."
        )

    return extracted