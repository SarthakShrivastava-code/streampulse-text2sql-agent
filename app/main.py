import os
import sys

# Ensure project root directory is in Python path.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import pandas as pd
import plotly.express as px

from app.llm_agent import generate_sql
from database.schema import get_database_connection, get_schema_info
from database.security import is_sql_safe


st.set_page_config(page_title="StreamPulse Text2SQL", page_icon="📊", layout="wide")

st.title("StreamPulse Text2SQL")
st.markdown("Ask questions about your data in plain English.")

if "db_conn" not in st.session_state:
    st.session_state.db_conn = get_database_connection()

conn = st.session_state.db_conn
schema_info = get_schema_info()

st.success("Groq API key detected.")

user_question = st.text_area(
    "Your question",
    value="what are the total sales per product category?",
    height=100,
)

if st.button("Generate SQL", type="primary"):
    if not user_question.strip():
        st.warning("Please type a question.")
    else:
        with st.spinner("Generating and validating SQL..."):
            try:
                sql_query = generate_sql(user_question, schema_info)
                st.subheader("Generated SQL")
                st.code(sql_query, language="sql")

                is_safe, security_msg = is_sql_safe(sql_query)
                if not is_safe:
                    st.error(f"{security_msg}")
                else:
                    df = conn.execute(sql_query).fetchdf()

                    st.subheader("Query Results")
                    if df.empty:
                        st.info("Query executed successfully, but returned 0 results.")
                    else:
                        st.dataframe(df, use_container_width=True)

                        if len(df.columns) >= 2:
                            st.subheader("Data Visualization")
                            x_col = df.columns[0]
                            y_col = df.columns[1]
                            fig = px.bar(
                                df,
                                x=x_col,
                                y=y_col,
                                title=f"{y_col} by {x_col}",
                                template="plotly_white",
                            )
                            st.plotly_chart(fig, use_container_width=True)
            except Exception as error:
                st.error(f"SQL Execution Error: {error}")
