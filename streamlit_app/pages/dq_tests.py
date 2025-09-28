import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from services import db
from utils.interactive_charts import create_scatter_chart, create_box_chart
import plotly.graph_objects as go

def run():
    """Interactive Data Quality Tests playground using Plotly selections."""
    if st.session_state.get("allow_access", 0) != 1:
        st.error("🔒 Please log in to access this page")
        return

    st.title("🧪 DQ Tests – Interactive Charts")
    st.caption("Fully interactive charts using WebGL rendering for optimal performance.")

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        days = st.selectbox("Date Range", [7, 30, 90], index=0, format_func=lambda d: f"Last {d} days")
        start_date = datetime.now() - timedelta(days=days)
        end_date = datetime.now()
    with col2:
        status = st.selectbox("Status", ["All", "pass", "fail"], index=0)
    with col3:
        limit = st.slider("Max rows", 100, 5000, 1000, step=100)

    # Load a compact dataset from dq_test_results
    try:
        query = (
            "SELECT execution_timestamp, dq_dimension, domain, table_name, dq_score, records_tested, status "
            "FROM dbt.dq_test_results WHERE execution_timestamp BETWEEN %s AND %s "
        )
        params = (start_date, end_date)
        if status != "All":
            query += " AND status = %s"
            params = (start_date, end_date, status)
        query += " ORDER BY execution_timestamp DESC LIMIT %s"
        params = (*params, limit)

        df = db.execute_query(query, params)
        if df.empty:
            st.info("No results for selected filters.")
            return
        df["execution_timestamp"] = pd.to_datetime(df["execution_timestamp"])  # ensure datetime
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        return

    # Interactive scatter chart using HTML components for true WebGL rendering
    st.markdown("### 📊 Test Scores Over Time")
    
    create_scatter_chart(
        df=df,
        x_col="execution_timestamp", 
        y_col="dq_score",
        color_col="dq_dimension",
        hover_data=["domain", "table_name", "status", "records_tested"],
        title="Test Scores Over Time (WebGL)",
        height=450
    )
    
    st.info("🎯 **Fully Interactive**: Zoom, pan, select, and hover - all powered by WebGL rendering!")

    # Interactive box plot by dimension
    st.markdown("---")
    st.markdown("### 📦 Score Distribution by Dimension")
    
    create_box_chart(
        df=df,
        y_col="dq_score",
        group_col="dq_dimension", 
        title="Score Distribution by Dimension",
        height=400
    )
    
    st.success("✅ **WebGL Powered**: These charts use Canvas rendering for smooth interactions!")


# Allow running this file standalone with `streamlit run`
if __name__ == "__main__":
    run()
