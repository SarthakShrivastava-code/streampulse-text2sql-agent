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

# --- Page Configuration ---
st.set_page_config(
    page_title="StreamPulse Text2SQL", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS Styling ---
st.markdown("""
<style>
    /* Global Canvas Background */
    .stApp {
        background-color: #EAEBED !important;
        color: #111827 !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Off-White Clean Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #FAFAFA !important;
        border-right: 1px solid #E2E4E8 !important;
        padding-top: 1rem !important;
    }

    /* Sidebar Collapse Button Styling (Dark & Visible) */
    button[data-testid="stSidebarCollapseButton"],
    button[data-testid="stSidebarCollapseButton"] svg,
    button[data-testid="stSidebarCollapseButton"] path {
        color: #1A1C1E !important;
        fill: #1A1C1E !important;
        stroke: #1A1C1E !important;
    }
    button[data-testid="stSidebarCollapseButton"] {
        background-color: #E2E4E8 !important;
        border-radius: 8px !important;
        padding: 6px 10px !important;
        border: 1px solid #CBD5E1 !important;
    }
    button[data-testid="stSidebarCollapseButton"]:hover {
        background-color: #CBD5E1 !important;
    }

    /* Dark Panel for Sidebar Radio (NO Orange Circle) */
    div[data-testid="stRadio"] input[type="radio"] {
        accent-color: #FFFFFF !important;
    }
    div[data-testid="stRadio"] > div {
        background-color: #2B2D31 !important;
        padding: 12px !important;
        border-radius: 14px !important;
        border: 1px solid #1A1C1E !important;
        gap: 8px !important;
    }
    div[data-testid="stRadio"] label, div[data-testid="stRadio"] label p {
        color: #FFFFFF !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
    }

    /* File Uploader Container & Button Styling (Pure White Text) */
    div[data-testid="stFileUploader"] section {
        background-color: #2B2D31 !important;
        border: 1px solid #1A1C1E !important;
        border-radius: 14px !important;
    }
    div[data-testid="stFileUploader"] button {
        background-color: #374151 !important;
        color: #FFFFFF !important;
        border: 1px solid #4B5563 !important;
        border-radius: 10px !important;
    }
    div[data-testid="stFileUploader"] button *,
    div[data-testid="stFileUploader"] button p,
    div[data-testid="stFileUploader"] button span,
    div[data-testid="stFileUploader"] button svg {
        color: #FFFFFF !important;
        fill: #FFFFFF !important;
    }
    div[data-testid="stFileUploader"] button:hover {
        background-color: #4B5563 !important;
        color: #FFFFFF !important;
    }
    div[data-testid="stFileUploader"] small {
        color: #D1D5DB !important;
    }

    /* Sidebar Headers & Upload Label Text */
    section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] p {
        color: #374151 !important;
        font-weight: 600 !important;
    }

    /* Main Section Typography */
    h1, h2, h3, h4 {
        color: #1A1C1E !important;
        font-weight: 800 !important;
        letter-spacing: -0.025em;
    }

    /* Primary CTA Button & Navigation Buttons */
    div.stButton > button {
        background-color: #2B2D31 !important;
        color: #FFFFFF !important;
        border: none !important;
        font-weight: 700 !important;
        border-radius: 20px !important;
        padding: 10px 22px !important;
        font-size: 0.92rem !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08) !important;
    }
    div.stButton > button:hover {
        background-color: #1A1C1E !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
    }

    /* Active Nav Button Styling */
    div.stButton > button[kind="primary"] {
        background-color: #111827 !important;
        color: #FFFFFF !important;
        border: 1px solid #000000 !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25) !important;
    }

    /* Text Inputs & Textarea */
    .stTextArea textarea, .stTextInput input {
        background-color: #FFFFFF !important;
        color: #1A1C1E !important;
        border: 1px solid #E2E4E8 !important;
        border-radius: 16px !important;
        padding: 14px 18px !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.02) !important;
    }

    /* Executive Summary Panel */
    .summary-box {
        background-color: #FFFFFF;
        border: 1px solid #E2E4E8;
        padding: 20px 24px;
        border-radius: 18px;
        margin-bottom: 20px;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.02);
    }

    /* Hero Metric Cards */
    .metric-card-dark {
        background-color: #2B2D31;
        color: #FFFFFF !important;
        padding: 20px 24px;
        border-radius: 18px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    }
    .metric-card-dark p, .metric-card-dark h2 {
        color: #FFFFFF !important;
    }
    
    .metric-card-light {
        background-color: #FFFFFF;
        border: 1px solid #E2E4E8;
        padding: 20px 24px;
        border-radius: 18px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.02);
    }

    /* Header Badges */
    .pill-badge-active {
        background-color: #7C7D7E;
        color: #FFFFFF;
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 0.82rem;
        font-weight: 600;
        display: inline-block;
    }
    .pill-badge-light {
        background-color: #FFFFFF;
        color: #4B5563;
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 0.82rem;
        font-weight: 500;
        border: 1px solid #E2E4E8;
        display: inline-block;
    }

    /* Code Block Formatting */
    .stCodeBlock {
        border: 1px solid #E2E4E8 !important;
        border-radius: 14px !important;
        background-color: #2B2D31 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Hero Title Section ---
col_title, col_controls = st.columns([2.8, 1.2])
with col_title:
    st.markdown("<h1 style='margin-bottom: 0; font-size: 3.4rem; font-weight: 900; color: #111827; letter-spacing: -0.03em;'>StreamPulse Text2SQL</h1>", unsafe_allow_html=True)

with col_controls:
    st.markdown("""
        <div style="text-align: right; padding-top: 22px;">
            <span class="pill-badge-active">Engine: DuckDB</span>
            <span class="pill-badge-light">Model: Groq</span>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)

# --- Initialize DuckDB Connection & Persisted State Keys ---
if "db_conn" not in st.session_state:
    st.session_state.db_conn = duckdb.connect(database=":memory:")
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

if "active_tab" not in st.session_state:
    st.session_state.active_tab = "Visualization"

if "query_results" not in st.session_state:
    st.session_state.query_results = None

conn = st.session_state.db_conn

def get_table_schema_vertical(table_name: str) -> str:
    """Formats column metadata vertically line-by-line for clear readability."""
    try:
        desc_df = conn.execute(f"DESCRIBE {table_name}").fetchdf()
        lines = [f"📊 TABLE: {table_name}", "─" * 28]
        for _, row in desc_df.iterrows():
            lines.append(f"• {row['column_name']} ({row['column_type']})")
        return "\n".join(lines)
    except Exception:
        return ""

# --- Sidebar Controls ---
with st.sidebar:
    st.markdown("### Active Source Mode")
    data_source = st.radio("Source Mode", ["Backend Sample Data", "Upload Custom File (CSV/Excel)"], label_visibility="collapsed")
    
    st.markdown("<hr style='border: none; border-top: 1px solid #E2E4E8; margin: 20px 0;'>", unsafe_allow_html=True)
    
    if data_source == "Upload Custom File (CSV/Excel)":
        uploaded_file = st.file_uploader("Upload Dataset", type=["csv", "tsv", "xlsx", "xls"])
        if uploaded_file is not None:
            raw_table_name = st.text_input("Target Table Name:", "custom_data")
            try:
                file_ext = uploaded_file.name.split(".")[-1].lower()
                registered_name = register_uploaded_file(
                    con=conn, 
                    file_source=uploaded_file.getvalue(), 
                    table_name=raw_table_name,
                    file_type=file_ext
                )
                schema_info = get_table_schema_vertical(registered_name)
                st.success(f"Registered '{registered_name}'")
                st.markdown("**Active Schema (Vertical):**")
                st.code(schema_info, language="text")
            except Exception as e:
                st.error(f"Error loading file: {e}")
                schema_info = ""
        else:
            schema_info = ""
            st.info("Upload a dataset to begin.")
    else:
        schema_info = get_table_schema_vertical("products") + "\n\n" + get_table_schema_vertical("sales")
        st.markdown("**Active Schema (Vertical):**")
        st.code(schema_info, language="text")

# --- Query Inputs ---
st.markdown("<h3 style='font-size: 1.1rem; font-weight: 700; color: #111827; margin-bottom: 8px;'>Ask Questions in Plain English</h3>", unsafe_allow_html=True)
user_question = st.text_area(
    "User Prompt Input",
    placeholder="e.g., What are the top 3 product categories by total sales amount?",
    height=85,
    label_visibility="collapsed"
)

col_btn, _ = st.columns([1, 3.5])
with col_btn:
    generate_clicked = st.button("Generate SQL & Execute", use_container_width=True)

# Execute query and store output in st.session_state
if generate_clicked:
    if not schema_info:
        st.error("Please upload a dataset or select 'Backend Sample Data' first.")
    elif not user_question.strip():
        st.warning("Please enter a question.")
    else:
        with st.spinner("Analyzing context & generating SQL..."):
            flat_schema = schema_info.replace("\n• ", ", ").replace("\n", " ")
            sql_query = generate_sql(user_question, flat_schema)
            
            try:
                validate_read_only_query(sql_query, dialect="duckdb")
                df = None
                try:
                    df = conn.execute(sql_query).fetchdf()
                except Exception as execution_err:
                    st.warning(f"⚠️ SQL Execution Error: {execution_err}")
                    st.info("🤖 Agentic Loop Triggered: Attempting automatic SQL repair...")
                    
                    try:
                        sql_query = auto_heal_sql(user_question, flat_schema, sql_query, str(execution_err))
                        validate_read_only_query(sql_query, dialect="duckdb")
                        df = conn.execute(sql_query).fetchdf()
                        st.success("✅ Self-healing successful! Query repaired.")
                    except Exception as heal_err:
                        st.error(f"❌ Auto-repair failed: {heal_err}")

                if df is not None:
                    summary = generate_executive_summary(user_question, df.head(10).to_string())
                    st.session_state.query_results = {
                        "df": df,
                        "sql_query": sql_query,
                        "summary": summary
                    }

            except (SQLSecurityViolation, ValueError) as sec_err:
                st.error(f"❌ Security Guardrail Blocked Execution: {sec_err}")

# --- Render Results ---
if st.session_state.query_results is not None:
    res = st.session_state.query_results
    df = res["df"]
    sql_query = res["sql_query"]
    summary = res["summary"]

    st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
    
    # Executive Narrative Box
    st.markdown(f"""
        <div class="summary-box">
            <h4 style="margin: 0 0 6px 0; color: #1A1C1E; font-size: 0.95rem; font-weight: 700;">💡 EXECUTIVE SUMMARY</h4>
            <p style="margin: 0; color: #4B5563; font-size: 0.95rem; line-height: 1.5;">{summary}</p>
        </div>
    """, unsafe_allow_html=True)

    # Top Row Metrics Cards
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.markdown(f"""
            <div class="metric-card-dark">
                <p style="margin: 0; font-size: 0.85rem; color: #D1D5DB !important;">Returned Rows</p>
                <h2 style="margin: 6px 0 0 0; color: #FFFFFF !important; font-size: 1.8rem;">{len(df):,}</h2>
            </div>
        """, unsafe_allow_html=True)
    with col_m2:
        st.markdown(f"""
            <div class="metric-card-light">
                <p style="margin: 0; font-size: 0.85rem; color: #6C727F;">Returned Columns</p>
                <h2 style="margin: 6px 0 0 0; color: #1A1C1E !important; font-size: 1.8rem;">{len(df.columns)}</h2>
            </div>
        """, unsafe_allow_html=True)
    with col_m3:
        st.markdown(f"""
            <div class="metric-card-light">
                <p style="margin: 0; font-size: 0.85rem; color: #6C727F;">Execution Status</p>
                <h2 style="margin: 6px 0 0 0; color: #1A1C1E !important; font-size: 1.8rem;">SUCCESS</h2>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # Pill Navigation Buttons
    col_t1, col_t2, col_t3, _ = st.columns([1.2, 1.2, 1.2, 4])
    with col_t1:
        if st.button("📈 Visualization", type="primary" if st.session_state.active_tab == "Visualization" else "secondary", use_container_width=True):
            st.session_state.active_tab = "Visualization"
            st.rerun()
    with col_t2:
        if st.button("📊 Query Results", type="primary" if st.session_state.active_tab == "Query Results" else "secondary", use_container_width=True):
            st.session_state.active_tab = "Query Results"
            st.rerun()
    with col_t3:
        if st.button("💻 Executed SQL", type="primary" if st.session_state.active_tab == "Executed SQL" else "secondary", use_container_width=True):
            st.session_state.active_tab = "Executed SQL"
            st.rerun()

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    # Tab Content View
    if st.session_state.active_tab == "Visualization":
        if not df.empty and len(df.columns) >= 2:
            fig = px.bar(
                df, 
                x=df.columns[0], 
                y=df.columns[1], 
                title=f"{df.columns[1]} by {df.columns[0]}",
                template="plotly_white"
            )
            fig.update_traces(
                marker_color="#2B2D31", 
                marker_line_color="#1A1C1E", 
                marker_line_width=1,
                width=0.4
            )
            fig.update_layout(
                paper_bgcolor="#FFFFFF",
                plot_bgcolor="#FFFFFF",
                font=dict(color="#111827", family="sans-serif", size=12),
                title_font=dict(color="#111827", size=16),
                xaxis=dict(
                    title_font=dict(color="#111827", size=13),
                    tickfont=dict(color="#111827", size=11),
                    showgrid=False
                ),
                yaxis=dict(
                    title_font=dict(color="#111827", size=13),
                    tickfont=dict(color="#111827", size=11),
                    gridcolor="#E2E4E8"
                ),
                margin=dict(l=30, r=30, t=50, b=30)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Requires at least 2 columns to render chart.")

    elif st.session_state.active_tab == "Query Results":
        if df.empty:
            st.info("Query executed successfully, but returned 0 rows.")
        else:
            st.dataframe(df, use_container_width=True, height=350)

    elif st.session_state.active_tab == "Executed SQL":
        st.markdown("**Validated Read-Only SQL Query:**")
        st.code(sql_query, language="sql")