import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from services import db
from utils.interactive_charts import create_scatter_chart, create_box_chart
import plotly.graph_objects as go

# DQ Dimensions mapping (for visualization)
DQ_DIMENSIONS = {
    'completeness': {'name': 'Completeness', 'color': '#FF6B6B'},
    'uniqueness': {'name': 'Uniqueness', 'color': '#4ECDC4'},
    'validity': {'name': 'Validity', 'color': '#45B7D1'},
    'consistency': {'name': 'Consistency', 'color': '#96CEB4'},
    'accuracy': {'name': 'Accuracy', 'color': '#FECA57'},
}

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
        # Get available domains
        try:
            domain_query = "SELECT DISTINCT domain FROM column_kpi ORDER BY domain"
            domain_df = db.execute_query(domain_query)
            available_domains = ["All"] + domain_df['domain'].tolist() if not domain_df.empty else ["All", "sales", "hr"]
        except:
            available_domains = ["All", "sales", "hr"]
        
        selected_domain = st.selectbox("Domain", available_domains, index=0)
    with col3:
        limit = st.slider("Max rows", 100, 5000, 1000, step=100)

    # Load a compact dataset from column_kpi table
    try:
        query = """
            SELECT 
                execution_timestamp, 
                domain, 
                table_name, 
                column_name,
                completeness_score,
                uniqueness_score,
                consistency_score,
                validity_score,
                accuracy_score,
                column_score
            FROM column_kpi 
            WHERE execution_timestamp BETWEEN %s AND %s 
        """
        params = [start_date, end_date]
        
        if selected_domain != "All":
            query += " AND domain = %s"
            params.append(selected_domain)
        
        query += " ORDER BY execution_timestamp DESC LIMIT %s"
        params.append(limit)

        df = db.execute_query(query, tuple(params))
        
        if df.empty:
            st.info("No results for selected filters.")
            return
            
        df["execution_timestamp"] = pd.to_datetime(df["execution_timestamp"])
        
        # Reshape data: melt dimension scores into long format for visualization
        dimension_cols = ['completeness_score', 'uniqueness_score', 'consistency_score', 
                         'validity_score', 'accuracy_score']
        
        df_melted = df.melt(
            id_vars=['execution_timestamp', 'domain', 'table_name', 'column_name', 'column_score'],
            value_vars=dimension_cols,
            var_name='dq_dimension',
            value_name='dq_score'
        )
        
        # Clean up dimension names
        df_melted['dq_dimension'] = df_melted['dq_dimension'].str.replace('_score', '')
        
        # Remove rows with null scores
        df_melted = df_melted.dropna(subset=['dq_score'])
        
        # Add a display name for hover
        df_melted['full_name'] = df_melted['table_name'] + '.' + df_melted['column_name']
        
        # Show summary
        st.success(f"✅ Loaded {len(df):,} column records → {len(df_melted):,} dimension scores for analysis")
        
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        st.info("💡 Tip: Check your database connection and ensure column_kpi table exists")
        return

    # Interactive scatter chart using HTML components for true WebGL rendering
    st.markdown("### 📊 Test Scores Over Time")
    
    try:
        create_scatter_chart(
            df=df_melted,
            x_col="execution_timestamp", 
            y_col="dq_score",
            color_col="dq_dimension",
            hover_data=["domain", "table_name", "column_name", "column_score"],
            title="Dimension Scores Over Time (WebGL)",
            height=450
        )
        
        st.info("🎯 **Fully Interactive**: Zoom, pan, select, and hover - all powered by WebGL rendering!")
    except Exception as e:
        st.error(f"Error creating scatter chart: {e}")

    # Interactive box plot by dimension
    st.markdown("---")
    st.markdown("### 📦 Score Distribution by Dimension")
    
    try:
        create_box_chart(
            df=df_melted,
            y_col="dq_score",
            group_col="dq_dimension", 
            title="Score Distribution by Dimension",
            height=400
        )
        
        st.success("✅ **WebGL Powered**: These charts use Canvas rendering for smooth interactions!")
    except Exception as e:
        st.error(f"Error creating box chart: {e}")

    # Additional analysis: Column performance
    st.markdown("---")
    st.markdown("### 🎯 Column Performance Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**📊 Top 10 Best Performing Columns**")
        top_columns = df.nlargest(10, 'column_score')[['table_name', 'column_name', 'column_score']]
        top_columns['full_name'] = top_columns['table_name'] + '.' + top_columns['column_name']
        st.dataframe(
            top_columns[['full_name', 'column_score']].rename(columns={'full_name': 'Column', 'column_score': 'Score'}),
            use_container_width=True,
            hide_index=True
        )
    
    with col2:
        st.markdown("**📉 Top 10 Worst Performing Columns**")
        bottom_columns = df.nsmallest(10, 'column_score')[['table_name', 'column_name', 'column_score']]
        bottom_columns['full_name'] = bottom_columns['table_name'] + '.' + bottom_columns['column_name']
        st.dataframe(
            bottom_columns[['full_name', 'column_score']].rename(columns={'full_name': 'Column', 'column_score': 'Score'}),
            use_container_width=True,
            hide_index=True
        )

    # Data preview section
    st.markdown("---")
    st.markdown("### 📋 Data Preview")
    
    with st.expander("View Raw Data", expanded=False):
        st.dataframe(
            df,
            use_container_width=True,
            height=400
        )
        
        # Download button
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download Data as CSV",
            data=csv,
            file_name=f"dq_tests_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )


# Allow running this file standalone with `streamlit run`
if __name__ == "__main__":
    run()