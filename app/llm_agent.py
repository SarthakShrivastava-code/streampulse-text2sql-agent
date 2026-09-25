import os
import streamlit as st
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

def _get_api_key() -> str | None:
    """Resolve the Groq key from local environment or Streamlit secrets."""
    api_key = os.getenv("GROQ_API_KEY")
    if api_key:
        return api_key

    try:
        api_key = st.secrets.get("GROQ_API_KEY")
    except Exception:
        api_key = None

    return api_key or None


client: Groq | None = None


def _get_client() -> Groq:
    global client
    if client is None:
        api_key = _get_api_key()
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not configured in the environment or Streamlit secrets.")
        client = Groq(api_key=api_key)
    return client

MODEL_NAME = "gemma2-9b-it"

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
    
    response = _get_client().chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_question}
        ],
        temperature=0.1
    )
    
    raw_content = response.choices[0].message.content.strip()
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
    
    response = _get_client().chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "system", "content": system_prompt}],
        temperature=0.1
    )
    
    return _extract_sql(response.choices[0].message.content.strip())

def generate_executive_summary(user_question: str, df_data_sample: str) -> str:
    """Generates a 2-sentence executive summary based on query results."""
    system_prompt = """
    You are a senior data analyst. Provide a concise, professional 2-sentence business summary of the query results. Focus on key metrics, trends, or notable findings.
    """
    
    user_prompt = f"User Question: {user_question}\nData Sample:\n{df_data_sample}"
    
    response = _get_client().chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.3
    )
    
    return response.choices[0].message.content.strip()

def _extract_sql(raw_content: str) -> str:
    """Helper to extract clean SQL from LLM markdown wrappers."""
    if "```sql" in raw_content:
        return raw_content.split("```sql")[1].split("```")[0].strip()
    elif "```" in raw_content:
        return raw_content.split("```")[1].split("```")[0].strip()
    return raw_content.strip()