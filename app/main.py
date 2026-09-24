import sys
import os

# Ensure project root directory is in Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import pandas as pd
import plotly.express as px
import duckdb

from database.schema import register_uploaded_file, sanitize_table_name
from database.security import validate_read_only_query, SQLSecurityViolation
from app.llm_agent import generate_sql, auto_heal_sql, generate_executive_summary

st.set_page_config(page_title="StreamPulse Text2SQL", page_icon="📊", layout="wide")
st.title("StreamPulse Text2SQL Agent")

# Initialize DuckDB Session Connection
if "db_conn" not in st.session_state:
    st.session_state.db_conn = duckdb.connect(database=":memory:")
    # Seed default sample dataset if not present
    st.session_state.db_conn.execute("""
        CREATE TABLE products (product_id INT, product_name VARCHAR, category VARCHAR, price DOUBLE);
        INSERT INTO products VALUES 
            (1, 'Laptop Pro', 'Electronics', 1200.00),
            (2, 'Wireless Mouse', 'Electronics', 25.00),
            (3, 'Mechanical Keyboard', 'Electronics', 85.00),
            (4, 'Standing Desk', 'Furniture', 450.00),
            (5, 'Ergonomic Chair', 'Furniture', 299.00);
            
        CREATE TABLE sales (sale_id INT, product_id INT, quantity INT, sale_date DATE, total_amount DOUBLE);
        INSERT INTO sales VALUES 
            (101, 1, 2, '2025-01-15', 2400.00),
            (102, 2, 5, '2025-01-16', 125.00),
            (103, 3, 3, '2025-01-18', 255.00),
            (104, 4, 1, '2025-01-20', 450.00),
            (105, 5, 2, '2025-02-01', 598.00);
    """)

conn = st.session_state.db_conn

def get_table_schema_prompt(table_name: str) -> str:
    """Helper to fetch column schema metadata for prompt injection."""
    try:
        desc_df = conn.execute(f"DESCRIBE {table_name}").fetchdf()
        cols = ", ".join([f"{row['column_name']} ({row['column_type']})" for _, row in desc_df.iterrows()])
        return f"Table {table_name} [{cols}]"
    except Exception:
        return ""

# Sidebar Controls
with st.sidebar:
    st.header("📁 Data Source Selection")
    data_source = st.radio("Select Mode:", ["Backend Sample Data", "Upload Custom File (CSV/Excel)"])
    
    if data_source == "Upload Custom File (CSV/Excel)":
        uploaded_file = st.file_uploader("Upload CSV, TSV, or Excel dataset", type=["csv", "tsv", "xlsx", "xls"])
        if uploaded_file is not None:
            raw_table_name = st.text_input("Assign Table Name:", "custom_data")
            try:
                # Call Developer A's file registration function
                file_ext = uploaded_file.name.split(".")[-1].lower()
                registered_name = register_uploaded_file(
                    con=conn, 
                    file_source=uploaded_file.getvalue(), 
                    table_name=raw_table_name,
                    file_type=file_ext
                )
                schema_info = get_table_schema_prompt(registered_name)
                st.success(f"Table '{registered_name}' registered successfully!")
                st.code(schema_info, language="text")
            except Exception as e:
                st.error(f"Error loading file: {e}")
                schema_info = ""
        else:
            schema_info = ""
            st.info("Upload a file above to begin querying.")
    else:
        # Default Schema Context
        schema_info = get_table_schema_prompt("products") + "\n" + get_table_schema_prompt("sales")
        st.code(schema_info, language="text")

# User Query Box
user_question = st.text_area("Ask a question about your data in plain English:", height=100)

if st.button("Generate SQL", type="primary"):
    if not schema_info:
        st.error("Please upload a file or select 'Backend Sample Data' first.")
    elif not user_question.strip():
        st.warning("Please enter a question.")
    else:
        with st.spinner("Translating natural language to SQL..."):
            try:
                sql_query = generate_sql(user_question, schema_info)
            except ValueError as gen_err:
                st.error(f"❌ SQL generation error: {gen_err}")
                st.stop()
            
            # Developer A's AST Security Check
            try:
                validate_read_only_query(sql_query, dialect="duckdb")
                st.subheader("Generated SQL")
                st.code(sql_query, language="sql")
                
                # Execution with Agentic Self-Healing Loop
                df = None
                try:
                    df = conn.execute(sql_query).fetchdf()
                except Exception as execution_err:
                    st.warning(f"⚠️ SQL Execution Error: {execution_err}")
                    st.info("🤖 Agentic Loop Triggered: Attempting automatic SQL repair...")
                    
                    try:
                        sql_query = auto_heal_sql(user_question, schema_info, sql_query, str(execution_err))
                        # Re-validate security on auto-healed query
                        validate_read_only_query(sql_query, dialect="duckdb")
                        
                        st.subheader("Repaired SQL")
                        st.code(sql_query, language="sql")
                        
                        df = conn.execute(sql_query).fetchdf()
                        st.success("✅ Self-healing successful! Query executed.")
                    except ValueError as heal_value_err:
                        st.error(f"❌ SQL repair error: {heal_value_err}")
                    except Exception as heal_err:
                        st.error(f"❌ Auto-repair failed: {heal_err}")

                # Output Display & Narrative Summarization
                if df is not None:
                    st.subheader("Query Results")
                    if df.empty:
                        st.info("Query executed successfully, but returned 0 rows.")
                    else:
                        st.dataframe(df, use_container_width=True)
                        
                        # Generate Executive Narrative
                        with st.spinner("Generating executive summary..."):
                            summary = generate_executive_summary(user_question, df.head(10).to_string())
                            st.info(f"💡 **Executive Summary:** {summary}")
                        
                        # Plotly Chart
                        if len(df.columns) >= 2:
                            st.subheader("Data Visualization")
                            fig = px.bar(df, x=df.columns[0], y=df.columns[1], title=f"{df.columns[1]} by {df.columns[0]}")
                            st.plotly_chart(fig, use_container_width=True)

            except (SQLSecurityViolation, ValueError) as sec_err:
                st.error(f"❌ Security/Validation Error: {sec_err}")