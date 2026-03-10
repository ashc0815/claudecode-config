"""
Streamlit UI for the AI Fraud Investigation Agent.

Launch: streamlit run frontend/app.py
"""

import sys
from pathlib import Path

import streamlit as st

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

st.set_page_config(
    page_title="AI Fraud Investigator",
    page_icon="🔍",
    layout="wide",
)

st.title("AI Fraud Investigation Agent")
st.caption("Multi-agent system for suspicious transaction detection and SAR report generation")

# Sidebar — Configuration
with st.sidebar:
    st.header("Configuration")
    api_key = st.text_input("Anthropic API Key", type="password")
    st.divider()
    st.subheader("Analysis Settings")
    max_transactions = st.slider("Max transactions to analyze", 10, 500, 100)
    confidence_threshold = st.slider("Confidence threshold", 0.0, 1.0, 0.7)

# Main content
tab1, tab2, tab3 = st.tabs(["Upload & Analyze", "Investigation Results", "SAR Report"])

with tab1:
    st.subheader("Upload Transaction Data")
    uploaded_file = st.file_uploader(
        "Upload CSV file (PaySim format or custom)",
        type=["csv"],
    )

    if uploaded_file:
        import pandas as pd

        df = pd.read_csv(uploaded_file, nrows=max_transactions)
        st.dataframe(df.head(20), use_container_width=True)

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Transactions", len(df))
        col2.metric("Total Amount", f"${df['amount'].sum():,.2f}" if "amount" in df.columns else "N/A")
        col3.metric("Unique Entities", df["nameOrig"].nunique() if "nameOrig" in df.columns else "N/A")

        if st.button("Start Investigation", type="primary"):
            st.info("Investigation pipeline starting... (connect orchestrator here)")
            # TODO: Wire up orchestrator
            # batch = load_sample_batch(uploaded_file)
            # orchestrator = Orchestrator()
            # state = orchestrator.investigate(batch)

with tab2:
    st.subheader("Investigation Results")
    st.info("Upload and analyze transactions to see results here.")

    # Placeholder for results display
    # - Anomaly flags with confidence bars
    # - Entity network graph (plotly)
    # - Risk assessment with reasoning chain

with tab3:
    st.subheader("SAR Report")
    st.info("Complete an investigation to generate a SAR report.")

    # Placeholder for SAR report display
    # - Formatted report with evidence chain
    # - Download as PDF button
    # - Export as JSON button
