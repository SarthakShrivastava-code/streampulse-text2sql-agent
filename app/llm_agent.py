import os

from dotenv import load_dotenv
from groq import Groq


load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def generate_sql(user_question: str, schema_info: str) -> str:
    system_prompt = f"""
    You are an expert SQL translation agent. Translate user questions into valid DuckDB SQL queries.

    Database Schema:
    {schema_info}

    Rules:
    1. Output ONLY executable SQL inside markdown code blocks like ```sql ... ```. No extra commentary.
    2. Only write SELECT queries. Never write DROP, DELETE, INSERT, or UPDATE statements.
    3. Match table and column names exactly as defined in the schema.
    """

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_question},
        ],
        temperature=0.1,
    )

    raw_content = response.choices[0].message.content.strip()

    if "```sql" in raw_content:
        raw_content = raw_content.split("```sql", 1)[1].split("```", 1)[0].strip()
    elif "```" in raw_content:
        raw_content = raw_content.split("```", 1)[1].split("```", 1)[0].strip()

    return raw_content
