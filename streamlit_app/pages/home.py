#My Hope Page
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from session_manager import session_manager
from services import db
from utils.interactive_charts import create_bar_chart, create_interactive_chart
import plotly.graph_objects as go

def create_metric_card(title, value, subtitle="", trend=None, color="#2563eb"):
    """Create a professional metric card without icons"""
    trend_html = ""
    if trend is not None:
        trend_color = "#10b981" if trend >= 0 else "#ef4444"
        trend_symbol = "↗" if trend >= 0 else "↘"
        trend_html = f'<div style="color: {trend_color}; font-size: 0.875rem; font-weight: 500; margin-top: 0.5rem;">{trend_symbol} {abs(trend):.1f}% vs last period</div>'
    
    return f"""
    <div style="
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        transition: all 0.2s ease;
        height: 100%;
    " onmouseover="this.style.boxShadow='0 4px 12px rgba(0, 0, 0, 0.15)'" onmouseout="this.style.boxShadow='0 1px 3px rgba(0, 0, 0, 0.1)'">
        <div style="color: {color}; font-size: 2.25rem; font-weight: 700; line-height: 1; margin-bottom: 0.5rem;">{value}</div>
        <div style="color: #374151; font-size: 1rem; font-weight: 600; margin-bottom: 0.25rem;">{title}</div>
        <div style="color: #6b7280; font-size: 0.875rem;">{subtitle}</div>
        {trend_html}
    </div>
    """

def create_comparison_card(title, current_value, historical_value, subtitle="", color="#2563eb"):
    """Create a comparison card showing current vs historical with delta indicator"""
    
    # Convert values to float, handling both string and numeric inputs
    try:
        if isinstance(current_value, str):
            current_float = float(current_value.replace('%', ''))
        else:
            current_float = float(current_value)
    except (ValueError, TypeError):
        current_float = 0.0
    
    try:
        if isinstance(historical_value, str):
            historical_float = float(historical_value.replace('%', ''))
        else:
            historical_float = float(historical_value)
    except (ValueError, TypeError):
        historical_float = 0.0
    
    # Calculate delta
    if historical_float > 0:
        delta = ((current_float - historical_float) / historical_float) * 100
    else:
        delta = 0
    
    delta_color = "#10b981" if delta >= 0 else "#ef4444"
    delta_symbol = "↑" if delta >= 0 else "↓"
    delta_text = f"{delta_symbol}{abs(delta):.1f}%"
    
    return f"""
    <div style="
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        transition: all 0.2s ease;
        height: 100%;
    " onmouseover="this.style.boxShadow='0 4px 12px rgba(0, 0, 0, 0.15)'" onmouseout="this.style.boxShadow='0 1px 3px rgba(0, 0, 0, 0.1)'">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
            <div style="color: {color}; font-size: 2rem; font-weight: 700;">{current_value}</div>
            <div style="color: {delta_color}; font-size: 1.2rem; font-weight: 600;">{delta_text}</div>
        </div>
        <div style="color: #374151; font-size: 1rem; font-weight: 600; margin-bottom: 0.25rem;">{title}</div>
        <div style="color: #6b7280; font-size: 0.875rem; margin-bottom: 0.5rem;">{subtitle}</div>
    </div>
    """

def create_domain_performance_card(domain, metrics, color="#2563eb"):
    """Create an enhanced domain performance card"""
    return f"""
    <div style="
        background: linear-gradient(135deg, {color}15 0%, {color}05 100%);
        border: 2px solid {color}40;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        transition: all 0.2s ease;
    " onmouseover="this.style.boxShadow='0 6px 20px rgba(0, 0, 0, 0.15)'" onmouseout="this.style.boxShadow='0 4px 12px rgba(0, 0, 0, 0.1)'">
        <div style="display: grid; grid-template-columns: 2fr 1fr 1fr 1fr 1fr 1fr; gap: 1rem; align-items: center;">
            <div>
                <h3 style="color: {color}; font-size: 1.5rem; font-weight: 700; margin: 0;">{metrics.get('global_score', 0):.1f}%</h3>
                <p style="color: #374151; font-size: 1.1rem; font-weight: 600; margin: 0;">{domain.upper()}</p>
            </div>
            <div style="text-align: center;">
                <div style="color: #374151; font-size: 1.2rem; font-weight: 600;">{metrics.get('total_tables', 0)}</div>
                <div style="color: #6b7280; font-size: 0.8rem;">Tables</div>
            </div>
            <div style="text-align: center;">
                <div style="color: #374151; font-size: 1.2rem; font-weight: 600;">{metrics.get('total_columns', 0)}</div>
                <div style="color: #6b7280; font-size: 0.8rem;">Columns</div>
            </div>
            <div style="text-align: center;">
                <div style="color: #10b981; font-size: 1.2rem; font-weight: 600;">{metrics.get('passing_tables', 0)}</div>
                <div style="color: #6b7280; font-size: 0.8rem;">Passing</div>
            </div>
            <div style="text-align: center;">
                <div style="color: #ef4444; font-size: 1.2rem; font-weight: 600;">{metrics.get('failing_tables', 0)}</div>
                <div style="color: #6b7280; font-size: 0.8rem;">Failing</div>
            </div>
            <div style="text-align: center;">
                <div style="color: #7c3aed; font-size: 1.2rem; font-weight: 600;">{metrics.get('total_tests', 0)}</div>
                <div style="color: #6b7280; font-size: 0.8rem;">Tests</div>
            </div>
        </div>
    </div>
    """

def create_enhanced_alert_card(message, alert_type="info"):
    """Create enhanced alert cards with better styling"""
    colors = {
        "info": {"bg": "#f0f9ff", "border": "#0ea5e9", "text": "#0c4a6e"},
        "success": {"bg": "#f0fdf4", "border": "#22c55e", "text": "#166534"},
        "warning": {"bg": "#fffbeb", "border": "#f59e0b", "text": "#92400e"},
        "error": {"bg": "#fef2f2", "border": "#ef4444", "text": "#dc2626"}
    }
    
    color_scheme = colors.get(alert_type, colors["info"])
    
    return f"""
    <div style="
        background: {color_scheme['bg']};
        border: 1px solid {color_scheme['border']};
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    ">
        <p style="color: {color_scheme['text']}; margin: 0; font-size: 0.9rem; line-height: 1.4;">
            {message}
        </p>
    </div>
    """

def create_dimension_summary_card(dimension, metrics, color="#2563eb"):
    """Create a dimension summary card without test details"""
    
    return f"""
    <div style="
        background: white;
        border: 1px solid #e5e7eb;
        border-left: 4px solid {color};
        border-radius: 8px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        transition: all 0.2s ease;
    " onmouseover="this.style.boxShadow='0 4px 12px rgba(0, 0, 0, 0.15)'" onmouseout="this.style.boxShadow='0 1px 3px rgba(0, 0, 0, 0.1)'">
        <div style="display: flex; justify-content: between; align-items: center; margin-bottom: 1rem;">
            <h3 style="color: #1f2937; font-size: 1.1rem; font-weight: 600; margin: 0; text-transform: capitalize;">{dimension.upper()}</h3>
            <div style="color: {color}; font-size: 1.3rem; font-weight: 700;">{metrics.get('avg_score', 0):.1f}%</div>
        </div>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem;">
            <div style="text-align: center;">
                <div style="color: #374151; font-size: 1.1rem; font-weight: 600;">{metrics.get('total_tests', 0)}</div>
                <div style="color: #6b7280; font-size: 0.8rem;">Total Tests</div>
            </div>
            <div style="text-align: center;">
                <div style="color: #10b981; font-size: 1.1rem; font-weight: 600;">{metrics.get('passed_tests', 0)}</div>
                <div style="color: #6b7280; font-size: 0.8rem;">Passed</div>
            </div>
            <div style="text-align: center;">
                <div style="color: #ef4444; font-size: 1.1rem; font-weight: 600;">{metrics.get('failed_tests', 0)}</div>
                <div style="color: #6b7280; font-size: 0.8rem;">Failed</div>
            </div>
        </div>
    </div>
    """

def create_enhanced_alert_card(message, alert_type="info"):
    """Create enhanced alert cards with better styling"""
    colors = {
        "info": {"bg": "#f0f9ff", "border": "#0ea5e9", "text": "#0c4a6e"},
        "success": {"bg": "#f0fdf4", "border": "#22c55e", "text": "#166534"},
        "warning": {"bg": "#fffbeb", "border": "#f59e0b", "text": "#92400e"},
        "error": {"bg": "#fef2f2", "border": "#ef4444", "text": "#dc2626"}
    }
    
    color_scheme = colors.get(alert_type, colors["info"])
    
    return f"""
    <div style="
        background: {color_scheme['bg']};
        border: 1px solid {color_scheme['border']};
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    ">
        <p style="color: {color_scheme['text']}; margin: 0; font-size: 0.9rem; line-height: 1.4;">
            {message}
        </p>
    </div>
    """

def get_historical_metrics(days_back, is_admin=False, user_domains=None):
    """Get historical metrics for comparison"""
    try:
        # Get global metrics from specific historical point
        global_query = f"""
        SELECT 
            AVG(global_score_weighted_by_columns) as global_score,
            COUNT(DISTINCT domain) as domains_covered,
            COUNT(DISTINCT database_name) as databases_covered,
            COUNT(*) as total_records,
            MAX(execution_timestamp) as last_execution
        FROM global_kpi g1
        WHERE g1.execution_timestamp = (
            SELECT MAX(execution_timestamp) 
            FROM global_kpi g2 
            WHERE g2.execution_timestamp <= DATE_SUB(CURDATE(), INTERVAL {days_back} DAY)
        )
        """
        
        # Apply domain filtering for non-admin users
        if not is_admin and user_domains:
            domain_list = "','".join(user_domains)
            global_query += f" AND g1.domain IN ('{domain_list}')"
        
        global_result = db.run_query(global_query)
        
        if not global_result.empty:
            row = global_result.iloc[0]
            global_metrics = {
                'global_score': float(row['global_score']) if row['global_score'] else 0,
                'domains_covered': int(row['domains_covered']) if row['domains_covered'] else 0,
                'databases_covered': int(row['databases_covered']) if row['databases_covered'] else 0,
                'total_records': int(row['total_records']) if row['total_records'] else 0,
                'last_execution': row['last_execution']
            }
        else:
            global_metrics = {
                'global_score': 0, 'domains_covered': 0, 'databases_covered': 0,
                'total_records': 0, 'last_execution': None
            }
        
        # Get historical table metrics using your actual table structure
        table_query = f"""
        SELECT 
            domain,
            AVG(table_score) as avg_score,
            COUNT(DISTINCT table_name) as tables,
            COUNT(*) as total_records,
            SUM(num_columns) as total_columns,
            MAX(execution_timestamp) as last_execution
        FROM table_kpi t1
        WHERE t1.execution_timestamp = (
            SELECT MAX(execution_timestamp) 
            FROM table_kpi t2 
            WHERE t2.execution_timestamp <= DATE_SUB(CURDATE(), INTERVAL {days_back} DAY)
        )
        """
        
        # Apply domain filtering for non-admin users
        if not is_admin and user_domains:
            domain_list = "','".join(user_domains)
            table_query += f" AND t1.domain IN ('{domain_list}')"
        
        table_query += " GROUP BY domain ORDER BY avg_score DESC"
        
        domain_metrics = db.run_query(table_query)
        
        return {
            'global': global_metrics,
            'domains': domain_metrics
        }
        
    except Exception as e:
        st.error(f"Error getting historical metrics: {e}")
        return {
            'global': {'global_score': 0, 'domains_covered': 0, 'databases_covered': 0, 'total_records': 0, 'last_execution': None},
            'domains': pd.DataFrame()
        }

def get_test_metadata(db):
    """Get test metadata from DBT-generated table"""
    query = """
    SELECT * FROM dq_test_metadata 
    WHERE created_at = (SELECT MAX(created_at) FROM dq_test_metadata)
    ORDER BY level, domain, table_name, column_name
    """
    return db.run_query(query)

def get_table_test_count(domain, table_name, metadata_df):
    """Get test count for specific table from metadata"""
    table_meta = metadata_df[
        (metadata_df['level'] == 'table') & 
        (metadata_df['domain'] == domain) & 
        (metadata_df['table_name'] == table_name)
    ]
    return int(table_meta.iloc[0]['total_tests']) if not table_meta.empty else 0

def get_domain_test_totals(domain, metadata_df):
    """Get total test counts for a domain"""
    domain_meta = metadata_df[
        (metadata_df['level'] == 'domain') & 
        (metadata_df['domain'] == domain)
    ]
    if not domain_meta.empty:
        return {
            'total_tests': int(domain_meta.iloc[0]['total_tests']),
            'total_tables': int(domain_meta.iloc[0]['table_count']),
            'total_columns': int(domain_meta.iloc[0]['column_count'])
        }
    return {'total_tests': 0, 'total_tables': 0, 'total_columns': 0}


def run():
    """Enhanced Data Quality Dashboard Home Page with Modern Features"""
    
    # Check authentication
    if st.session_state.get("allow_access", 0) != 1:
        st.error("Access denied. Please log in to continue.")
        return
    
    # Get user info
    current_user = st.session_state.get("current_user", "Unknown")
    is_admin = st.session_state.get("is_admin", False)
    user_domains = st.session_state.get("domains", [])
    
    # Enhanced page configuration with modern styling
    st.markdown("""
    <style>
    .main .block-container {
        padding: 1rem !important;
        max-width: none !important;
    }
    
    .header-container {
        background: linear-gradient(135deg, #1e40af 0%, #3b82f6 50%, #60a5fa 100%);
        padding: 2rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        color: white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        position: relative;
        overflow: hidden;
    }
    
    .header-container::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.1'%3E%3Ccircle cx='30' cy='30' r='2'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E") repeat;
        opacity: 0.3;
    }
    
    .header-content {
        position: relative;
        z-index: 1;
    }
    
    .section-header {
        color: #1f2937;
        font-size: 1.5rem;
        font-weight: 600;
        margin: 2rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #e5e7eb;
        position: relative;
    }
    
    .section-header::after {
        content: '';
        position: absolute;
        bottom: -2px;
        left: 0;
        width: 60px;
        height: 2px;
        background: linear-gradient(90deg, #3b82f6, #60a5fa);
    }
    
    .metric-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 1.5rem;
        margin-bottom: 2rem;
    }
    
    .stTab > div > div > div > div {
        gap: 0.5rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Enhanced header with modern design
    st.markdown(f"""
    <div class="header-container">
        <div class="header-content">
            <h1 style="font-size: 2.5rem; margin: 0 0 0.5rem 0; font-weight: 700;">Data Quality Dashboard</h1>
            <p style="font-size: 1.125rem; margin: 0; opacity: 0.9;">Welcome back, {current_user}</p>
            <p style="font-size: 0.875rem; margin: 0.5rem 0 0 0; opacity: 0.8;">
                {'🔑 System Administrator' if is_admin else f'📊 Domain Access: {", ".join([d.upper() for d in user_domains])}'}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Data Status
    st.markdown('<div class="section-header">📊 Current Data Quality Status</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])

    with col1:
        st.info("📊 **Current Status**: Showing latest test run results for all metrics")

    with col2:
        if st.button("🔄 Refresh Data", key="refresh_home_data"):
            st.rerun()

    # Load latest test run data
    try:
        # Get latest execution timestamp for each domain
        latest_global_query = """
        SELECT 
            g1.execution_timestamp,
            g1.domain,
            g1.database_name,
            g1.global_score_weighted_by_columns as global_score
        FROM global_kpi g1
        INNER JOIN (
            SELECT domain, MAX(execution_timestamp) as latest_execution
            FROM global_kpi
            GROUP BY domain
        ) g2 ON g1.domain = g2.domain AND g1.execution_timestamp = g2.latest_execution
        ORDER BY g1.execution_timestamp DESC
        """
        
        latest_table_query = """
        SELECT 
            t1.execution_timestamp,
            t1.domain,
            t1.schema_name,
            t1.table_name,
            t1.avg_completeness_score,
            t1.avg_uniqueness_score,
            t1.avg_consistency_score,
            t1.avg_validity_score,
            t1.avg_accuracy_score,
            t1.table_score,
            t1.num_columns
        FROM table_kpi t1
        INNER JOIN (
            SELECT domain, table_name, MAX(execution_timestamp) as latest_execution
            FROM table_kpi
            GROUP BY domain, table_name
        ) t2 ON t1.domain = t2.domain 
            AND t1.table_name = t2.table_name 
            AND t1.execution_timestamp = t2.latest_execution
        ORDER BY t1.execution_timestamp DESC
        """
        
        df_global = db.run_query(latest_global_query)  # Note: change from execute_query to run_query
        df_table = db.run_query(latest_table_query)
        
        # Check if data exists
        if df_global.empty or df_table.empty:
            st.warning("⚠️ No data quality test results found.")
            st.info("💡 Try running your data quality tests first to populate the data.")
            return
            
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return

    # Apply domain filtering for non-admin users
    if not is_admin and user_domains:
        df_global = df_global[df_global['domain'].isin(user_domains)]
        df_table = df_table[df_table['domain'].isin(user_domains)]

    # Calculate metrics from latest data
    latest_global = df_global.copy()
    latest_table = df_table.copy()

    total_tables = len(latest_table)
    total_columns = int(latest_table['num_columns'].sum()) if not latest_table.empty else 0

    if not latest_global.empty:
        if len(latest_global) > 1:
            # Weight by columns for multi-domain average
            domain_weights = latest_table.groupby('domain')['num_columns'].sum()
            domain_scores = latest_global.set_index('domain')['global_score']
            weighted_sum = sum(domain_scores.get(domain, 0) * weight for domain, weight in domain_weights.items())
            global_avg_score = weighted_sum / total_columns if total_columns > 0 else 0
        else:
            global_avg_score = latest_global['global_score'].iloc[0]
    else:
        global_avg_score = 0

    passing_tables = len(latest_table[latest_table['table_score'] >= 80]) if not latest_table.empty else 0
    failing_tables = total_tables - passing_tables

    
    # Load test metadata once
    try:
        test_metadata = get_test_metadata(db)
    except Exception as e:
        st.warning(f"Could not load test metadata: {e}")
        test_metadata = pd.DataFrame()  # Fallback to empty dataframe

    # Use actual counts from metadata
    total_test_runs = len(latest_table)
    total_test_checks = 0

    # Get actual test counts from metadata
    for domain in latest_table['domain'].unique():
        domain_totals = get_domain_test_totals(domain, test_metadata)
        total_test_checks += domain_totals['total_tests']

    total_test_checks = int(total_test_checks)

    # Global Metrics Section (V2 Style - 5 columns)
    st.markdown('<div class="section-header">🌍 Global Data Quality Metrics</div>', unsafe_allow_html=True)

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown(create_metric_card(
            "Overall Score",
            f"{global_avg_score:.1f}%",
            "Average across all tables",
            None,  # No trend for now
            "#2563eb"
        ), unsafe_allow_html=True)

    with col2:
        st.markdown(create_metric_card(
            "Tables Covered",
            str(total_tables),
            "Under monitoring",
            color="#059669"
        ), unsafe_allow_html=True)

    with col3:
        st.markdown(create_metric_card(
            "Test Runs",
            str(total_test_runs),
            "Total executions",
            color="#7c3aed"
        ), unsafe_allow_html=True)

    with col4:
        st.markdown(create_metric_card(
            "Test Checks",
            str(total_test_checks),
            "Implemented validations",
            color="#8b5cf6"
        ), unsafe_allow_html=True)

    with col5:
        pass_rate = (passing_tables / total_tables * 100) if total_tables > 0 else 0
        st.markdown(create_metric_card(
            "Pass Rate",
            f"{pass_rate:.1f}%",
            f"{passing_tables} of {total_tables} tables ≥80%",
            color="#dc2626" if pass_rate < 80 else "#059669"
        ), unsafe_allow_html=True)

    # Detailed Score Breakdown Section
    st.markdown('<div class="section-header">📊 Score Calculation Breakdown</div>', unsafe_allow_html=True)

    # Show how the global score is calculated
    st.markdown("""
    <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1.5rem; margin-bottom: 1.5rem;">
        <h4 style="color: #1e293b; margin: 0 0 1rem 0;">How the Global Score is Calculated</h4>
        <p style="color: #64748b; margin: 0; line-height: 1.6;">
            The global score is the <strong>simple average of all table scores</strong>. Each table's score is calculated as the 
            <strong>average of all dimension scores</strong> for that table. Individual dimension scores are based on data quality test results:
        </p>
        <ul style="color: #64748b; margin: 0.5rem 0 0 0; padding-left: 1.5rem;">
            <li><strong>Completeness:</strong> Percentage of non-null values</li>
            <li><strong>Uniqueness:</strong> Percentage of unique values where expected</li>
            <li><strong>Consistency:</strong> Values conform to business rules</li>
            <li><strong>Validity:</strong> Values match expected format/domain</li>
            <li><strong>Accuracy:</strong> Values meet accuracy requirements</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    # Show detailed breakdown using your actual table data
    if not latest_table.empty:
        # Show breakdown in tabs
        tab1, tab2 = st.tabs(["📋 Table Performance Details", "📈 Test Results Summary"])
        
        with tab1:
            st.markdown("**Table-Level Performance:**")
            
            # Create enhanced dataframe display with your available data
            display_df = latest_table[['domain', 'table_name', 'table_score', 'num_columns']].copy()
            # display_df['Quality Grade'] = display_df['table_score'].apply(
            #     lambda x: 'A+' if x >= 95 else 'A' if x >= 90 else 'B+' if x >= 85 else 'B' if x >= 80 else 'C' if x >= 70 else 'D'
            # )
            display_df['Status'] = display_df['table_score'].apply(
                lambda x: '✅ Excellent' if x >= 90 else '🟢 Good' if x >= 80 else '🟡 Needs Attention' if x >= 70 else '🔴 Critical'
            )
            
            # Add dimension breakdown for each table
            display_df['Completeness'] = latest_table['avg_completeness_score'].round(1)
            display_df['Uniqueness'] = latest_table['avg_uniqueness_score'].round(1)
            display_df['Consistency'] = latest_table['avg_consistency_score'].round(1)
            display_df['Validity'] = latest_table['avg_validity_score'].round(1)
            display_df['Validity'] = latest_table['avg_validity_score'].round(1)
            display_df['Accuracy'] = latest_table['avg_accuracy_score'].round(1)
            
            # Add estimated test counts based on your domain and table structure
            def get_estimated_tests_and_failures(row):
                table_name = row['table_name']
                domain = row['domain']
                table_score = row['table_score']
                
                # Get actual test count from metadata
                total_tests = get_table_test_count(domain, table_name, test_metadata)
                
                # Calculate failed tests based on table score
                passed_tests = int((table_score / 100) * total_tests)
                failed_tests = total_tests - passed_tests
                
                return total_tests, passed_tests, failed_tests
            
            # Apply the function to get test counts
            test_data = latest_table.apply(get_estimated_tests_and_failures, axis=1, result_type='expand')
            display_df['Total Tests'] = test_data[0]
            display_df['Passed Tests'] = test_data[1]
            display_df['Failed Tests'] = test_data[2]
            
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "domain": st.column_config.TextColumn("Domain", help="Data domain"),
                    "table_name": st.column_config.TextColumn("Table Name", help="Table identifier"),
                    "table_score": st.column_config.NumberColumn(
                        "Overall Score",
                        help="Overall quality score",
                        format="%.1f%%"
                    ),
                    "num_columns": st.column_config.NumberColumn(
                        "Columns",
                        help="Number of columns monitored"
                    ),
                    "Total Tests": st.column_config.NumberColumn(
                        "Total Tests",
                        help="Total number of tests for this table"
                    ),
                    "Passed Tests": st.column_config.NumberColumn(
                        "Passed Tests",
                        help="Number of tests that passed"
                    ),
                    "Failed Tests": st.column_config.NumberColumn(
                        "Failed Tests",
                        help="Number of tests that failed"
                    ),
                    "Completeness": st.column_config.NumberColumn(
                        "Completeness",
                        help="Average completeness score",
                        format="%.1f%%"
                    ),
                    "Uniqueness": st.column_config.NumberColumn(
                        "Uniqueness", 
                        help="Average uniqueness score",
                        format="%.1f%%"
                    ),
                    "Consistency": st.column_config.NumberColumn(
                        "Consistency",
                        help="Average consistency score", 
                        format="%.1f%%"
                    ),
                    "Validity": st.column_config.NumberColumn(
                        "Validity",
                        help="Average validity score",
                        format="%.1f%%"
                    ),
                    #"Quality Grade": st.column_config.TextColumn("Grade", help="Quality grade"),
                    "Status": st.column_config.TextColumn("Status", help="Current status")
                }
            )
        
        with tab2:
            st.markdown("**Global Score Calculation:**")
            
            # Show simple average calculation
            calculation_data = []
            for _, row in latest_table.iterrows():
                calculation_data.append({
                    'Table': row['table_name'],
                    'Domain': row['domain'],
                    'Score': row['table_score']
                })
            
            calc_df = pd.DataFrame(calculation_data)
            st.dataframe(
                calc_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Score": st.column_config.NumberColumn("Score", format="%.1f%%")
                }
            )
            
            average_score = latest_table['table_score'].mean()
            st.markdown(f"""
            <div style="background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 6px; padding: 1rem; margin-top: 1rem;">
                <strong>Formula:</strong> (Table 1 Score + Table 2 Score + ... + Table N Score) ÷ Number of Tables<br><br>
                <strong>Your Calculation:</strong><br>
                Total Tables: {len(latest_table)}<br>
                Sum of Scores: {latest_table['table_score'].sum():.1f}%<br>
                <strong>Global Score: {average_score:.1f}%</strong>
            </div>
            """, unsafe_allow_html=True)

    # Historical Comparison Section
    st.markdown('<div class="section-header">📈 Historical Comparison</div>', unsafe_allow_html=True)

    # Date range selector for historical comparison
    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        historical_days = st.selectbox(
            "Compare with",
            [7, 15, 30, 60, 90, 120, 180, 365],
            index=0,
            format_func=lambda x: f"Last {x} days",
            key="historical_comparison"
        )

    with col2:
        st.info(f"📊 **Historical Comparison**: Current scores vs {historical_days}-day average")

    with col3:
        if st.button("🔄 Refresh Historical Data", key="refresh_historical"):
            st.rerun()

    # Get historical metrics
    historical_metrics = get_historical_metrics(historical_days, is_admin, user_domains)

    # Global Historical Comparison Cards
    st.markdown("### 🌍 Global Metrics Comparison")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        current_score = global_avg_score
        historical_score = historical_metrics['global']['global_score']
        st.markdown(create_comparison_card(
            "Overall Score",
            f"{current_score:.1f}%",
            f"{historical_score:.1f}%",
            "Current vs Historical Average",
            "#2563eb"
        ), unsafe_allow_html=True)

    with col2:
        current_tables = total_tables
        if not historical_metrics['domains'].empty:
            historical_tables = historical_metrics['domains']['tables'].sum()  # Sum of tables across domains
        else:
            historical_tables = current_tables  # Fallback
        st.markdown(create_comparison_card(
            "Tables Covered",
            str(current_tables),
            str(historical_tables),
            "Current vs Historical Average",
            "#059669"
        ), unsafe_allow_html=True)

    with col3:
        current_test_runs = total_test_runs
        if not historical_metrics['domains'].empty:
            historical_test_runs = historical_metrics['domains']['total_records'].sum()
        else:
            historical_test_runs = current_test_runs  # Fallback
        st.markdown(create_comparison_card(
            "Test Runs",
            str(current_test_runs),
            str(historical_test_runs),
            "Current vs Historical Average",
            "#7c3aed"
        ), unsafe_allow_html=True)

    with col4:
        current_domains = len(df_global['domain'].unique()) if not df_global.empty else 0
        historical_domains = historical_metrics['global']['domains_covered']
        st.markdown(create_comparison_card(
            "Domains",
            str(current_domains),
            str(historical_domains),
            "Current vs Historical Average",
            "#8b5cf6"
        ), unsafe_allow_html=True)

    with col5:
        current_pass_rate = pass_rate
        # Fix: Calculate historical pass rate using same method as current
        if not historical_metrics['domains'].empty:
            # Current method: (passing_tables / total_tables * 100)
            historical_passing_tables = len(historical_metrics['domains'][historical_metrics['domains']['avg_score'] >= 80])
            historical_total_tables = len(historical_metrics['domains'])
            historical_pass_rate = (historical_passing_tables / historical_total_tables * 100) if historical_total_tables > 0 else 0
        else:
            historical_pass_rate = current_pass_rate
        
        st.markdown(create_comparison_card(
            "Pass Rate",
            f"{current_pass_rate:.1f}%",
            f"{historical_pass_rate:.1f}%",
            "Current vs Historical Average",
            "#dc2626" if current_pass_rate < 80 else "#059669"
        ), unsafe_allow_html=True)

    # Domain Historical Comparison
    if not historical_metrics['domains'].empty:
        st.markdown("### 📊 Domain Historical Comparison")
        
        # Display domain cards vertically (one under another)
        for _, current_domain_row in df_global.iterrows():
            domain = current_domain_row['domain']
            
            # Get historical data for this domain
            historical_domain = historical_metrics['domains'][historical_metrics['domains']['domain'] == domain]
            
            if not historical_domain.empty:
                hist_row = historical_domain.iloc[0]
                
                current_score = current_domain_row['global_score']
                historical_score = hist_row['avg_score']
                delta = ((current_score - historical_score) / historical_score * 100) if historical_score > 0 else 0
                delta_color = "#10b981" if delta >= 0 else "#ef4444"
                delta_symbol = "↑" if delta >= 0 else "↓"
                
                # Get current domain table metrics
                current_domain_tables = latest_table[latest_table['domain'] == domain]
                current_tables_count = len(current_domain_tables)
                current_columns_count = current_domain_tables['num_columns'].sum()
                
                # Get historical domain metrics
                historical_tables_count = int(hist_row['tables']) if 'tables' in hist_row and hist_row['tables'] else current_tables_count
                historical_columns_count = int(hist_row['total_columns']) if 'total_columns' in hist_row and hist_row['total_columns'] else current_columns_count
                
                # Calculate test metrics for this domain
                total_tests_domain = 0
                passed_tests_domain = 0
                failed_tests_domain = 0
                
                for _, table_row in current_domain_tables.iterrows():
                    table_name = table_row['table_name']
                    table_score = table_row['table_score']
                    
                    # Get actual test count from metadata
                    table_tests = get_table_test_count(domain, table_name, test_metadata)
                    
                    table_passed = int((table_score / 100) * table_tests)
                    table_failed = table_tests - table_passed
                    
                    total_tests_domain += table_tests
                    passed_tests_domain += table_passed
                    failed_tests_domain += table_failed
                
                # Calculate historical passed/failed tests
                historical_passed = int(historical_score/100 * total_tests_domain) if total_tests_domain > 0 else 0
                historical_failed = total_tests_domain - historical_passed
                
                # Create domain section header
                st.markdown(f"#### {domain.upper()} Domain - Historical Comparison")
                
                # Create horizontal comparison cards
                col1, col2, col3, col4, col5, col6 = st.columns(6)
                
                with col1:
                    st.markdown(create_comparison_card(
                        "Current Score",
                        f"{current_score:.1f}%",
                        f"{historical_score:.1f}%",
                        f"vs {historical_score:.1f}%",
                        delta_color
                    ), unsafe_allow_html=True)
                
                with col2:
                    st.markdown(create_comparison_card(
                        "Tables",
                        str(current_tables_count),
                        str(historical_tables_count),
                        f"vs {historical_tables_count}",
                        "#374151"
                    ), unsafe_allow_html=True)
                
                with col3:
                    st.markdown(create_comparison_card(
                        "Total Tests",
                        str(total_tests_domain),
                        str(total_tests_domain),  # Test configuration doesn't change historically
                        f"vs {total_tests_domain}",
                        "#7c3aed"
                    ), unsafe_allow_html=True)
                
                with col4:
                    st.markdown(create_comparison_card(
                        "Passed",
                        str(passed_tests_domain),
                        str(historical_passed),
                        f"vs {historical_passed}",
                        "#10b981"
                    ), unsafe_allow_html=True)
                
                with col5:
                    st.markdown(create_comparison_card(
                        "Failed",
                        str(failed_tests_domain),
                        str(historical_failed),
                        f"vs {historical_failed}",
                        "#ef4444"
                    ), unsafe_allow_html=True)
                
                with col6:
                    st.markdown(create_comparison_card(
                        "Columns",
                        str(current_columns_count),
                        str(historical_columns_count),
                        f"vs {historical_columns_count}",
                        "#059669"
                    ), unsafe_allow_html=True)
                
                st.markdown("---")  # Separator between domains

    # Dimension-Based Scoring Breakdown
    st.markdown('<div class="section-header">📊 Dimension-Based Scoring Breakdown</div>', unsafe_allow_html=True)

    # Get dimension metrics from the latest table data
    if not latest_table.empty:
        # Calculate dimension scores across all domains
        dimension_scores = {
            'Completeness': latest_table['avg_completeness_score'].mean(),
            'Uniqueness': latest_table['avg_uniqueness_score'].mean(),
            'Consistency': latest_table['avg_consistency_score'].mean(),
            'Validity': latest_table['avg_validity_score'].mean()
        }
        
        # Add Accuracy if it exists
        if 'avg_accuracy_score' in latest_table.columns:
            dimension_scores['Accuracy'] = latest_table['avg_accuracy_score'].mean()
        
        # Create dimension cards
        dim_col1, dim_col2 = st.columns(2)
        
        dimension_colors = {
            'Completeness': '#FF6B6B',
            'Uniqueness': '#4ECDC4', 
            'Validity': '#45B7D1',
            'Consistency': '#96CEB4',
            'Accuracy': '#FECA57'
        }
        
        for idx, (dimension, score) in enumerate(dimension_scores.items()):
            color = dimension_colors.get(dimension, '#6b7280')
            
            # Calculate dimension test counts using check type mapping
            dimension_tests = 0
            dimension_passed = 0
            dimension_failed = 0
            
            # Map check types to dimensions (updated)
            check_to_dimension = {
                'null': 'Completeness',
                'threshold': 'Completeness', 
                'uniqueness': 'Uniqueness',
                'consistency': 'Consistency',
                'validity': 'Validity',
                'regex': 'Validity',
                'domain': 'Validity', 
                'foreign_key': 'Validity',
                'accuracy': 'Accuracy'
            }

            if not test_metadata.empty:
                column_metadata = test_metadata[test_metadata['level'] == 'column']
                for _, col_row in column_metadata.iterrows():
                    if col_row['details'] and col_row['details'] != 'none':
                        check_types = [check.strip() for check in col_row['details'].split(',')]
                        for check_type in check_types:
                            if check_to_dimension.get(check_type) == dimension:
                                dimension_tests += 1
            # Calculate passed/failed for this dimension
            dimension_passed = int((score / 100) * dimension_tests) if dimension_tests > 0 else 0
            dimension_failed = dimension_tests - dimension_passed
                
            # Alternate between columns
            with (dim_col1 if idx % 2 == 0 else dim_col2):
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, {color}10 0%, {color}05 100%);
                    border: 1px solid {color}30;
                    border-radius: 8px;
                    padding: 1rem;
                    margin-bottom: 1rem;
                    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                ">
                    <h4 style="color: {color}; font-size: 1.1rem; font-weight: 600; margin: 0 0 0.5rem 0; text-transform: capitalize;">{dimension.upper()}</h4>
                    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.5rem; text-align: center;">
                        <div>
                            <div style="color: {color}; font-size: 1.1rem; font-weight: 600;">{score:.1f}%</div>
                            <div style="color: #6b7280; font-size: 0.7rem;">Avg Score</div>
                        </div>
                        <div>
                            <div style="color: #374151; font-size: 1.1rem; font-weight: 600;">{dimension_tests}</div>
                            <div style="color: #6b7280; font-size: 0.7rem;">Total</div>
                        </div>
                        <div>
                            <div style="color: #10b981; font-size: 1.1rem; font-weight: 600;">{dimension_passed}</div>
                            <div style="color: #6b7280; font-size: 0.7rem;">✅ Pass</div>
                        </div>
                        <div>
                            <div style="color: #ef4444; font-size: 1.1rem; font-weight: 600;">{dimension_failed}</div>
                            <div style="color: #6b7280; font-size: 0.7rem;">❌ Fail</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        # Add historical comparison for dimensions if available
        if not historical_metrics['domains'].empty:
            st.markdown("#### 📊 Dimension Historical Comparison")
            
            # Get actual historical dimension averages
            historical_dimension_query = f"""
            SELECT 
                AVG(avg_completeness_score) as hist_completeness,
                AVG(avg_uniqueness_score) as hist_uniqueness,
                AVG(avg_consistency_score) as hist_consistency,
                AVG(avg_validity_score) as hist_validity,
                AVG(avg_accuracy_score) as hist_accuracy
            FROM table_kpi
            WHERE execution_timestamp >= DATE_SUB(CURDATE(), INTERVAL {historical_days} DAY)
            AND execution_timestamp < CURDATE()
            """
            
            # Apply domain filtering for non-admin users
            if not is_admin and user_domains:
                domain_list = "','".join(user_domains)
                historical_dimension_query += f" AND domain IN ('{domain_list}')"
            
            try:
                historical_dims = db.run_query(historical_dimension_query)
                if not historical_dims.empty and len(historical_dims) > 0:
                    row = historical_dims.iloc[0]
                    historical_dimensions = {
                        'Completeness': float(row['hist_completeness']) if row['hist_completeness'] else dimension_scores['Completeness'],
                        'Uniqueness': float(row['hist_uniqueness']) if row['hist_uniqueness'] else dimension_scores['Uniqueness'],
                        'Consistency': float(row['hist_consistency']) if row['hist_consistency'] else dimension_scores['Consistency'],
                        'Validity': float(row['hist_validity']) if row['hist_validity'] else dimension_scores['Validity']
                    }
                    # Add Accuracy if it exists
                    if 'Accuracy' in dimension_scores:
                        historical_dimensions['Accuracy'] = float(row['hist_accuracy']) if row['hist_accuracy'] else dimension_scores['Accuracy']
                else:
                    # Fallback to current values if no historical data
                    historical_dimensions = dimension_scores.copy()
            except Exception as e:
                st.warning(f"Could not load historical dimension data: {e}")
                historical_dimensions = dimension_scores.copy()
            
            # Create comparison cards for dimensions
            dim_comp_col1, dim_comp_col2 = st.columns(2)
            
            for idx, (dimension, current_score) in enumerate(dimension_scores.items()):
                historical_score = historical_dimensions.get(dimension, current_score)
                delta = ((current_score - historical_score) / historical_score * 100) if historical_score > 0 else 0
                delta_color = "#10b981" if delta >= 0 else "#ef4444"
                delta_symbol = "↑" if delta >= 0 else "↓"
                color = dimension_colors.get(dimension, '#6b7280')
                
                # Alternate between columns
                with (dim_comp_col1 if idx % 2 == 0 else dim_comp_col2):
                    st.markdown(f"""
                    <div style="
                        background: linear-gradient(135deg, {delta_color}10 0%, {delta_color}05 100%);
                        border: 1px solid {delta_color}30;
                        border-radius: 8px;
                        padding: 1rem;
                        margin-bottom: 1rem;
                        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                    ">
                        <h4 style="color: {color}; font-size: 1.1rem; font-weight: 600; margin: 0 0 0.5rem 0; text-transform: capitalize;">{dimension.upper()}</h4>
                        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 0.5rem; text-align: center;">
                            <div>
                                <div style="color: {delta_color}; font-size: 1.2rem; font-weight: 600;">{current_score:.1f}%</div>
                                <div style="color: #6b7280; font-size: 0.7rem;">Current</div>
                            </div>
                            <div>
                                <div style="color: {delta_color}; font-size: 1.1rem; font-weight: 600;">{delta_symbol}{abs(delta):.1f}%</div>
                                <div style="color: #6b7280; font-size: 0.7rem;">Change</div>
                            </div>
                            <div>
                                <div style="color: #64748b; font-size: 1.1rem; font-weight: 600;">{historical_score:.1f}%</div>
                                <div style="color: #6b7280; font-size: 0.7rem;">Historical</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
    else:
        st.warning("⚠️ No table data available for dimension analysis")
    
    # Performance Analysis Section
    st.markdown('<div class="section-header">Performance Analysis</div>', unsafe_allow_html=True)

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        # Domain Performance Bar Chart
        st.markdown("**Average Score by Domain**")
        
        if not df_global.empty:
            # Define domain colors for the chart
            domain_colors = {
                'FINANCE': '#ef4444',    # Red
                'HR': '#3b82f6',         # Blue  
                'SALES': '#10b981',      # Green
                'MARKETING': '#f59e0b',  # Orange
                'OPERATIONS': '#8b5cf6', # Purple
                'IT': '#06b6d4',         # Cyan
                'CUSTOMER': '#ec4899',   # Pink
                'PRODUCT': '#84cc16'     # Lime
            }
            
            # Prepare data for domain performance chart
            domain_data = []
            domain_names = []
            domain_scores = []
            bar_colors = []
            
            for _, row in df_global.iterrows():
                domain = row['domain'].upper()
                score = row['global_score']
                domain_data.append(score)
                domain_names.append(domain)
                domain_scores.append(score)
                bar_colors.append(domain_colors.get(domain, '#6b7280'))
            
            # Create domain performance chart
            chart_data = {
                "data": [{
                    "x": domain_names,
                    "y": domain_scores,
                    "type": "bar",
                    "marker": {
                        "color": bar_colors,
                        "line": {"color": "white", "width": 1}
                    },
                    "text": [f"{score:.1f}%" for score in domain_scores],
                    "textposition": "outside",
                    "hovertemplate": "<b>%{x} Domain</b><br>Average Score: %{y:.1f}%<extra></extra>"
                }],
                "layout": {
                    "title": {"text": "Domain Performance Overview", "x": 0.5},
                    "xaxis": {"title": "Domain"},
                    "yaxis": {"title": "Average DQ Score (%)", "range": [0, 100]},
                    "height": 400,
                    "showlegend": False,
                    "shapes": [{
                        "type": "line",
                        "x0": 0, "x1": 1,
                        "y0": 80, "y1": 80,
                        "xref": "paper",
                        "yref": "y",
                        "line": {"color": "red", "dash": "dash", "width": 2},
                        "name": "Target: 80%"
                    }],
                    "annotations": [{
                        "x": 0.02, "y": 82,
                        "xref": "paper", "yref": "y",
                        "text": "Target: 80%",
                        "showarrow": False,
                        "font": {"color": "red", "size": 10}
                    }]
                }
            }
            
            create_interactive_chart(chart_data, height=400)
        else:
            st.info("No domain data available for chart")

    with chart_col2:
        # Historical Trend Chart
        st.markdown("**Quality Improvement Trajectory**")
        
        try:
            # Get historical trend data for the last 30 days
            trend_query = f"""
            SELECT 
                DATE(execution_timestamp) as test_date,
                domain,
                AVG(global_score_weighted_by_columns) as daily_avg_score
            FROM global_kpi
            WHERE execution_timestamp >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            """
            
            # Apply domain filtering for non-admin users
            if not is_admin and user_domains:
                domain_list = "','".join(user_domains)
                trend_query += f" AND domain IN ('{domain_list}')"
            
            trend_query += """
            GROUP BY DATE(execution_timestamp), domain
            ORDER BY test_date, domain
            """
            
            trend_df = db.run_query(trend_query)
            
            if not trend_df.empty:
                # Create trend lines for each domain
                traces = []
                
                for domain in trend_df['domain'].unique():
                    domain_data = trend_df[trend_df['domain'] == domain]
                    domain_color = domain_colors.get(domain.upper(), '#6b7280')
                    
                    traces.append({
                        "x": [d.strftime('%Y-%m-%d') for d in domain_data['test_date']],
                        "y": domain_data['daily_avg_score'].tolist(),
                        "type": "scatter",
                        "mode": "lines+markers",
                        "name": f"{domain.upper()} Domain",
                        "line": {"color": domain_color, "width": 3},
                        "marker": {"size": 6}
                    })
                
                trajectory_data = {
                    "data": traces,
                    "layout": {
                        "title": {"text": "30-Day Quality Trend", "x": 0.5},
                        "xaxis": {"title": "Date"},
                        "yaxis": {"title": "DQ Score (%)", "range": [0, 100]},
                        "height": 400,
                        "shapes": [{
                            "type": "line",
                            "x0": 0, "x1": 1,
                            "y0": 80, "y1": 80,
                            "xref": "paper",
                            "yref": "y",
                            "line": {"color": "red", "dash": "dash", "width": 2}
                        }],
                        "legend": {"x": 0.02, "y": 0.98}
                    }
                }
                
                create_interactive_chart(trajectory_data, height=400)
            else:
                st.info("No historical trend data available")
                
        except Exception as e:
            st.warning(f"Could not load trend data: {str(e)}")
            # Fallback message
            st.info("Historical trajectory analysis will be available once more test data is collected")

    # # Dimension Performance Radar Chart
    # st.markdown("**Dimension Performance Comparison**")

    # if not latest_table.empty:
    #     # Calculate dimension averages
    #     dimensions = ['Completeness', 'Uniqueness', 'Consistency', 'Validity']
    #     if 'avg_accuracy_score' in latest_table.columns:
    #         dimensions.append('Accuracy')
        
    #     # Create radar chart data for each domain
    #     radar_traces = []
        
    #     for domain in df_global['domain'].unique():
    #         domain_tables = latest_table[latest_table['domain'] == domain]
    #         domain_color = domain_colors.get(domain.upper(), '#6b7280')
            
    #         dimension_scores = []
    #         for dim in dimensions:
    #             col_name = f'avg_{dim.lower()}_score'
    #             if col_name in domain_tables.columns:
    #                 avg_score = domain_tables[col_name].mean()
    #                 dimension_scores.append(avg_score)
    #             else:
    #                 dimension_scores.append(0)
            
    #         # Add the first dimension at the end to close the radar chart
    #         dimension_scores.append(dimension_scores[0])
    #         radar_dimensions = dimensions + [dimensions[0]]
            
    #         radar_traces.append({
    #             "type": "scatterpolar",
    #             "r": dimension_scores,
    #             "theta": radar_dimensions,
    #             "fill": "toself",
    #             "name": f"{domain.upper()} Domain",
    #             "line": {"color": domain_color}
    #         })
        
    #     radar_data = {
    #         "data": radar_traces,
    #         "layout": {
    #             "polar": {
    #                 "radialaxis": {
    #                     "visible": True,
    #                     "range": [0, 100]
    #                 }
    #             },
    #             "showlegend": True,
    #             "title": {"text": "Dimension Performance by Domain", "x": 0.5},
    #             "height": 500
    #         }
    #     }
        
    #     create_interactive_chart(radar_data, height=500)
    # else:
    #     st.info("No table data available for dimension comparison")

    # Historical Performance Insights
    st.markdown('<div class="section-header">📊 Historical Performance Insights</div>', unsafe_allow_html=True)

    # Create insights columns
    insight_col1, insight_col2, insight_col3 = st.columns(3)

    with insight_col1:
        # Quality Trend Analysis
        st.markdown("**📈 Quality Trend Analysis**")
        try:
            # Get trend data for the last 7 days vs previous 7 days
            trend_query = f"""
            SELECT 
                r.recent_avg_score,
                p.previous_avg_score,
                r.recent_test_count,
                p.previous_test_count
            FROM 
                (SELECT 
                    AVG(global_score_weighted_by_columns) as recent_avg_score,
                    COUNT(*) as recent_test_count
                FROM global_kpi
                WHERE execution_timestamp >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
                ) r,
                (SELECT 
                    AVG(global_score_weighted_by_columns) as previous_avg_score,
                    COUNT(*) as previous_test_count
                FROM global_kpi
                WHERE execution_timestamp >= DATE_SUB(CURDATE(), INTERVAL 14 DAY)
                    AND execution_timestamp < DATE_SUB(CURDATE(), INTERVAL 7 DAY)
                ) p
            """
            
            # Apply domain filtering for non-admin users
            if not is_admin and user_domains:
                domain_list = "','".join(user_domains)
                # Add domain filter to both CTEs
                trend_query = trend_query.replace(
                    "FROM global_kpi", 
                    f"FROM global_kpi WHERE domain IN ('{domain_list}') AND execution_timestamp"
                )
            
            trend_df = db.run_query(trend_query)
            
            if not trend_df.empty and len(trend_df) > 0:
                row = trend_df.iloc[0]
                recent_score = row['recent_avg_score'] or 0
                previous_score = row['previous_avg_score'] or 0
                score_change = recent_score - previous_score
                
                # Display trend metrics
                st.metric(
                    "7-Day Avg Score", 
                    f"{recent_score:.1f}%",
                    delta=f"{score_change:+.1f}% vs previous week"
                )
                
                st.metric(
                    "Test Executions", 
                    f"{row['recent_test_count']}",
                    delta=f"{int(row['recent_test_count'] - row['previous_test_count']):+d} vs previous week"
                )
                
                # Trend indicator
                if score_change > 1:
                    st.success("📈 Quality is improving!")
                elif score_change < -1:
                    st.warning("📉 Quality needs attention")
                else:
                    st.info("➡️ Quality is stable")
            else:
                st.info("📊 Insufficient data for trend analysis")
                
        except Exception as e:
            st.warning(f"⚠️ Could not load trend data: {str(e)}")

    with insight_col2:
        # Performance by Domain
        st.markdown("**🎯 Performance by Domain**")
        try:
            if not df_global.empty:
                # Show best and worst performing domains
                best_domain = df_global.loc[df_global['global_score'].idxmax()]
                worst_domain = df_global.loc[df_global['global_score'].idxmin()]
                
                st.metric(
                    f"Best: {best_domain['domain'].title()}", 
                    f"{best_domain['global_score']:.1f}%",
                    delta="Leading performer"
                )
                
                st.metric(
                    f"Needs Work: {worst_domain['domain'].title()}", 
                    f"{worst_domain['global_score']:.1f}%",
                    delta="Focus area"
                )
                
                # Domain spread analysis
                score_spread = df_global['global_score'].max() - df_global['global_score'].min()
                if score_spread > 10:
                    st.warning(f"📊 High variation: {score_spread:.1f}% spread between domains")
                else:
                    st.success(f"📊 Consistent performance: {score_spread:.1f}% spread")
            else:
                st.info("📊 No domain data available")
                
        except Exception as e:
            st.warning(f"⚠️ Could not load domain data: {str(e)}")

    with insight_col3:
        # Test Volume & Coverage
        st.markdown("**📊 Test Volume & Coverage**")
        try:
            # Get current coverage metrics
            if not latest_table.empty and not df_global.empty:
                tables_covered = len(latest_table)
                domains_covered = len(df_global)
                columns_covered = latest_table['num_columns'].sum()
                
                # Get actual total tests from metadata
                if not test_metadata.empty:
                    # Sum up all domain totals
                    total_tests = 0
                    for domain in latest_table['domain'].unique():
                        domain_totals = get_domain_test_totals(domain, test_metadata)
                        total_tests += domain_totals['total_tests']
                # else:
                #     # Fallback calculation
                #     total_tests = 0
                #     for _, table_row in latest_table.iterrows():
                #         table_tests = get_table_test_count(table_row['domain'], table_row['table_name'], test_metadata)
                #         total_tests += table_tests if table_tests > 0 else 5  # fallback per table
                
                st.metric("Tables Covered", f"{tables_covered}")
                st.metric("Total Tests", f"{total_tests}")
                st.metric("Domains", f"{domains_covered}")
                
                # Coverage assessment
                if total_tests > 20:
                    st.success("✅ Comprehensive testing coverage")
                elif total_tests > 10:
                    st.info("📊 Good testing coverage")
                else:
                    st.warning("⚠️ Limited testing coverage")
            else:
                st.info("📊 No coverage data available")
                
        except Exception as e:
            st.warning(f"⚠️ Could not load coverage data: {str(e)}")

    # Show tables with issues
    st.markdown("**🚨 Tables Requiring Attention**")
    if not latest_table.empty:
        issues_df = latest_table[latest_table['table_score'] < 80].sort_values('table_score')
        
        if not issues_df.empty:
            # Define domain colors
            domain_colors = {
                'FINANCE': '#ef4444',    # Red
                'HR': '#3b82f6',         # Blue  
                'SALES': '#10b981',      # Green
                'MARKETING': '#f59e0b',  # Orange
                'OPERATIONS': '#8b5cf6', # Purple
                'IT': '#06b6d4',         # Cyan
            }
            
            for _, row in issues_df.head(5).iterrows():
                domain = row['domain'].upper()
                domain_color = domain_colors.get(domain, '#6b7280')
                
                # Determine severity color based on score
                if row['table_score'] < 50:
                    severity_color = '#dc2626'  # Red
                    severity_icon = '🔴'
                elif row['table_score'] < 70:
                    severity_color = '#ea580c'  # Orange
                    severity_icon = '🟠'
                else:
                    severity_color = '#d97706'  # Amber
                    severity_icon = '🟡'
                
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
                    border-left: 4px solid {severity_color};
                    border-radius: 8px;
                    padding: 1rem;
                    margin: 0.5rem 0;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="flex: 1;">
                            <div style="display: flex; align-items: center; margin-bottom: 0.25rem;">
                                <span style="
                                    background: {domain_color};
                                    color: white;
                                    padding: 0.25rem 0.5rem;
                                    border-radius: 4px;
                                    font-size: 0.75rem;
                                    font-weight: 600;
                                    margin-right: 0.5rem;
                                ">{domain}</span>
                                <span style="font-weight: 600; color: #374151;">{row['table_name']}</span>
                            </div>
                            <div style="color: #6b7280; font-size: 0.875rem;">
                                {row['num_columns']} columns monitored
                            </div>
                        </div>
                        <div style="text-align: right;">
                            <div style="display: flex; align-items: center; margin-bottom: 0.25rem;">
                                <span style="font-size: 1.2rem; margin-right: 0.25rem;">{severity_icon}</span>
                                <span style="
                                    color: {severity_color};
                                    font-size: 1.5rem;
                                    font-weight: 700;
                                ">{row['table_score']:.1f}%</span>
                            </div>
                            <div style="color: #6b7280; font-size: 0.75rem;">
                                Needs improvement
                            </div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="
                background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
                border: 1px solid #22c55e;
                border-radius: 12px;
                padding: 2rem;
                text-align: center;
                margin: 1rem 0;
            ">
                <div style="font-size: 3rem; margin-bottom: 1rem;">🎉</div>
                <h3 style="color: #166534; margin: 0 0 0.5rem 0;">All Tables Performing Well!</h3>
                <p style="color: #15803d; margin: 0;">No tables require immediate attention</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No table data available for analysis")

    # Quick Actions
    st.markdown('<div class="section-header">Quick Actions</div>', unsafe_allow_html=True)

    action_col2, action_col3 = st.columns(2)

    with action_col2:
        if st.button("📄 Export Report", use_container_width=True):
            # Prepare comprehensive export data
            export_data = []
            
            # Add global metrics
            for _, global_row in df_global.iterrows():
                export_data.append({
                    'Type': 'Global',
                    'Domain': global_row['domain'],
                    'Score': global_row['global_score'],
                    'Timestamp': global_row['execution_timestamp']
                })
            
            # Add table metrics
            for _, table_row in latest_table.iterrows():
                export_data.append({
                    'Type': 'Table',
                    'Domain': table_row['domain'],
                    'Table': table_row['table_name'],
                    'Score': table_row['table_score'],
                    'Columns': table_row['num_columns'],
                    'Completeness': table_row['avg_completeness_score'],
                    'Uniqueness': table_row['avg_uniqueness_score'],
                    'Consistency': table_row['avg_consistency_score'],
                    'Validity': table_row['avg_validity_score'],
                    'Timestamp': table_row['execution_timestamp']
                })
            
            if export_data:
                export_df = pd.DataFrame(export_data)
                csv_data = export_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download CSV",
                    data=csv_data,
                    file_name=f"dq_comprehensive_report_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.warning("No data available for export")

    with action_col3:
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # Footer
    st.markdown("---")
    footer_col1, footer_col2 = st.columns(2)

    with footer_col1:
        st.caption(f"Last updated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")

    with footer_col2:
        if st.button("Logout", key="logout_btn"):
            session_manager.logout()
            st.success("Logged out successfully!")
            st.rerun()