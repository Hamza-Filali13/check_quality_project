"""
Data Quality Analytics Dashboard - Integrated with DBT KPI Tables
Adapted for global_kpi, table_kpi, and column_kpi data structure
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
from session_manager import session_manager
from services import db
from utils.interactive_charts import create_interactive_chart, create_scatter_chart, create_box_chart
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Plotly configuration
PLOT_CONFIG = {
    "scrollZoom": False,
    "displaylogo": False,
    "displayModeBar": True,
    "staticPlot": False,
}

try:
    from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
    from st_aggrid.shared import GridUpdateMode
    HAS_AGGRID = True
except ImportError:
    HAS_AGGRID = False

# DQ Dimensions Configuration
DQ_DIMENSIONS = {
    'completeness': {
        'name': 'Completeness',
        'description': 'Measures the degree to which data is present and not missing',
        'color': '#FF6B6B',
        'icon': '📊'
    },
    'uniqueness': {
        'name': 'Uniqueness', 
        'description': 'Ensures no duplicate records exist where uniqueness is expected',
        'color': '#4ECDC4',
        'icon': '🔑'
    },
    'validity': {
        'name': 'Validity',
        'description': 'Data conforms to defined formats, ranges, and business rules',
        'color': '#45B7D1',
        'icon': '✅'
    },
    'consistency': {
        'name': 'Consistency',
        'description': 'Data is consistent across systems and over time',
        'color': '#96CEB4',
        'icon': '🔄'
    },
    'accuracy': {
        'name': 'Accuracy',
        'description': 'Data correctly represents the real-world entity it describes',
        'color': '#FECA57',
        'icon': '🎯'
    }
}

def log_user_action(action, details, user):
    """Log user actions for audit trail"""
    try:
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'user': user,
            'action': action,
            'details': json.dumps(details),
            'page': 'analytics'
        }
        print(f"User Action: {user} - {action} - {details}")
    except Exception as e:
        print(f"Error logging action: {e}")

def create_advanced_table(df, key="advanced_table", domain_filter=None):
    """Create an interactive table with selection capabilities"""
    if domain_filter:
        df = df[df['domain'].isin(domain_filter)]
    
    if not HAS_AGGRID:
        st.dataframe(df, use_container_width=True, key=key)
        return {'selected_rows': []}
    
    gb = GridOptionsBuilder.from_dataframe(df)
    
    gb.configure_selection(
        selection_mode='multiple',
        use_checkbox=True,
        groupSelectsChildren=True,
        groupSelectsFiltered=True
    )
    
    gb.configure_pagination(paginationAutoPageSize=True, paginationPageSize=20)
    gb.configure_side_bar()
    gb.configure_default_column(
        resizable=True, 
        filterable=True, 
        sortable=True, 
        groupable=True,
        flex=1
    )
    
    # Configure score columns with percentage formatting
    score_columns = ['column_score', 'completeness_score', 'uniqueness_score', 
                    'consistency_score', 'validity_score', 'accuracy_score', 'table_score', 'global_score']
    
    for col in score_columns:
        if col in df.columns:
            gb.configure_column(col, 
                              cellStyle={'textAlign': 'center'},
                              valueFormatter="value ? value.toFixed(1) + '%' : 'N/A'",
                              width=120)
    
    grid_options = gb.build()
    
    grid_response = AgGrid(
        df,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        allow_unsafe_jscode=True,
        theme='streamlit',
        key=key,
        height=400,
        width='100%'
    )
    
    return grid_response

def load_kpi_results(start_date=None, end_date=None, dimension_filter=None, domain_filter=None):
    """Load KPI results from your dbt tables"""
    try:
        # Base query combining all your KPI tables
        base_query = """
        SELECT 
            c.execution_timestamp,
            c.domain,
            c.schema_name,
            c.table_name,
            c.column_name,
            c.column_score,
            c.completeness_score,
            c.uniqueness_score,
            c.consistency_score,
            c.validity_score,
            c.accuracy_score,
            t.table_score,
            t.num_columns,
            t.avg_completeness_score,
            t.avg_uniqueness_score,
            t.avg_consistency_score,
            t.avg_validity_score,
            g.global_score_weighted_by_columns as global_score
        FROM column_kpi c
        LEFT JOIN table_kpi t ON c.execution_timestamp = t.execution_timestamp 
            AND c.domain = t.domain 
            AND c.table_name = t.table_name
        LEFT JOIN global_kpi g ON c.execution_timestamp = g.execution_timestamp 
            AND c.domain = g.domain
        WHERE 1=1
        """
        
        params = []
        
        # Add date filters
        if start_date and end_date:
            if start_date == end_date:
                base_query += " AND DATE(c.execution_timestamp) = %s"
                params.append(start_date)
            else:
                base_query += " AND DATE(c.execution_timestamp) BETWEEN %s AND %s"
                params.extend([start_date, end_date])
        
        # Add domain filter
        if domain_filter and isinstance(domain_filter, list) and len(domain_filter) > 0:
            placeholders = ','.join(['%s'] * len(domain_filter))
            base_query += f" AND c.domain IN ({placeholders})"
            params.extend(domain_filter)
        
        # ADD DIMENSION FILTER HERE
        if dimension_filter and dimension_filter != "All":
            dimension_column = f"{dimension_filter.lower()}_score"
            base_query += f" AND c.{dimension_column} IS NOT NULL"
        
        base_query += " ORDER BY c.execution_timestamp DESC"
        
        df = db.run_query_with_params(base_query, tuple(params)) if params else db.run_query(base_query)

        
        if not df.empty:
            df['execution_timestamp'] = pd.to_datetime(df['execution_timestamp'])
            
            # Add derived columns for analytics
            df['status'] = df['column_score'].apply(lambda x: 'pass ✅' if pd.notna(x) and x >= 80 else 'fail ❌')
            df['pass_rate'] = df['column_score'] / 100
            df['failure_rate'] = 1 - df['pass_rate']
        
        return df
        
    except Exception as e:
        st.error(f"Error loading KPI results: {e}")
        return pd.DataFrame()

def create_dimensional_summary(start_date=None, end_date=None, dimension_filter=None, domain_filter=None):
    """Create dimensional summary from your KPI data"""
    try:
        # Build query with filters using your column_kpi table
        base_conditions = ["1=1"]
        params = []

        if start_date and end_date:
            if start_date == end_date:
                base_conditions.append("DATE(execution_timestamp) = %s")
                params.append(start_date)
            else:
                base_conditions.append("DATE(execution_timestamp) BETWEEN %s AND %s")
                params.extend([start_date, end_date])
        
        if domain_filter and isinstance(domain_filter, list) and len(domain_filter) > 0:
            placeholders = ','.join(['%s'] * len(domain_filter))
            base_conditions.append(f"domain IN ({placeholders})")
            params.extend(domain_filter)
        
        where_clause = " AND ".join(base_conditions)
        
        # Query for each dimension separately from your column_kpi table
        dimensions_data = []
        
        dimension_columns = {
            'completeness': 'completeness_score',
            'uniqueness': 'uniqueness_score', 
            'consistency': 'consistency_score',
            'validity': 'validity_score',
            'accuracy': 'accuracy_score'
        }
        
        for dimension, column_name in dimension_columns.items():
            # Skip if filtering by specific dimension and this isn't it
            if dimension_filter and dimension_filter.lower() != dimension:
                continue
                
            query = f"""
            SELECT 
                '{dimension}' as dq_dimension,
                COUNT(CASE WHEN {column_name} IS NOT NULL THEN 1 END) as total_tests,
                COUNT(CASE WHEN {column_name} >= 80 THEN 1 END) as passed_tests,
                COUNT(CASE WHEN {column_name} < 80 AND {column_name} IS NOT NULL THEN 1 END) as failed_tests,
                AVG({column_name}) as avg_score,
                COUNT(DISTINCT domain) as domains_covered,
                COUNT(DISTINCT CONCAT(domain, '.', table_name)) as tables_covered
            FROM column_kpi
            WHERE {where_clause} AND {column_name} IS NOT NULL
            """
            
            result = db.run_query_with_params(query, tuple(params)) if params else db.run_query(query)
            
            if not result.empty and result.iloc[0]['total_tests'] > 0:
                dimensions_data.append(result.iloc[0])
        
        if dimensions_data:
            df = pd.DataFrame(dimensions_data)
            df['pass_rate'] = df['passed_tests'] / df['total_tests']
            df['overall_score'] = df['avg_score']
            return df
        else:
            return pd.DataFrame()
        
    except Exception as e:
        st.error(f"Error creating dimensional summary: {e}")
        return pd.DataFrame()

def get_global_dq_metrics(start_date=None, end_date=None, domain_filter=None):
    """Get global metrics from your KPI tables with proper filtering"""
    try:
        # Build base query with filters - use GLOBAL_KPI table for accurate global scores
        base_conditions = ["1=1"]
        params = []
        
        # Add date filters
        if start_date and end_date:
            if start_date == end_date:
                # Same day - use DATE() function for exact match
                base_conditions.append("DATE(execution_timestamp) = %s")
                params.append(start_date)
            else:
                # Date range
                base_conditions.append("DATE(execution_timestamp) BETWEEN %s AND %s")
                params.extend([start_date, end_date])
        else:
            # Default to today if no dates provided
            base_conditions.append("DATE(execution_timestamp) = CURDATE()")
        
        # Add domain filter
        if domain_filter and isinstance(domain_filter, list) and len(domain_filter) > 0:
            placeholders = ','.join(['%s'] * len(domain_filter))
            base_conditions.append(f"domain IN ({placeholders})")
            params.extend(domain_filter)
        
        where_clause = " AND ".join(base_conditions)
        
        # Query GLOBAL_KPI table for accurate global scores
        global_query = f"""
        SELECT 
            AVG(global_score_weighted_by_columns) as avg_global_score,
            COUNT(DISTINCT domain) as domains_tested,
            MIN(DATE(execution_timestamp)) as min_date,
            MAX(DATE(execution_timestamp)) as max_date,
            COUNT(DISTINCT DATE(execution_timestamp)) as days_with_data
        FROM global_kpi
        WHERE {where_clause}
        """
        
        # Query COLUMN_KPI table for detailed metrics
        column_query = f"""
        SELECT 
            COUNT(DISTINCT CONCAT(domain, '.', table_name)) as tables_tested,
            COUNT(*) as total_columns,
            COUNT(CASE WHEN column_score >= 80 THEN 1 END) as passed_columns,
            COUNT(CASE WHEN column_score < 80 THEN 1 END) as failed_columns,
            COUNT(CASE WHEN column_score < 60 THEN 1 END) as critical_failures
        FROM column_kpi
        WHERE {where_clause}
        """
        failing_record = f"""
        SELECT 
            COUNT(DISTINCT CONCAT(domain, '.', table_name)) as tables_tested,
            COUNT(*) as total_columns,
            COUNT(CASE WHEN column_score >= 80 THEN 1 END) as passed_columns,
            COUNT(CASE WHEN column_score < 80 THEN 1 END) as failed_columns,
            COUNT(CASE WHEN column_score < 60 THEN 1 END) as critical_failures
        FROM failing_records
        WHERE {where_clause}
        """
        
        global_result = db.run_query_with_params(global_query, tuple(params)) if params else db.run_query(global_query)
        column_result = db.run_query_with_params(column_query, tuple(params)) if params else db.run_query(column_query)
        
        if not global_result.empty and not column_result.empty:
            global_row = global_result.iloc[0]
            column_row = column_result.iloc[0]
            
            pass_rate = (column_row['passed_columns'] / column_row['total_columns'] * 100) if column_row['total_columns'] > 0 else 0
            
            metrics = {
                'total_tests': int(column_row['total_columns']),
                'passed_tests': int(column_row['passed_columns']),
                'failed_tests': int(column_row['failed_columns']),
                'pass_rate': pass_rate,
                'failure_rate': 100 - pass_rate,
                'avg_score': float(global_row['avg_global_score']) if global_row['avg_global_score'] else 0,  # Use ACTUAL global score
                'critical_failures': int(column_row['critical_failures']),
                'high_impact_failures': int(column_row['critical_failures']),
                'domains_tested': int(global_row['domains_tested']),
                'tables_tested': int(column_row['tables_tested']),
                'dimensions_covered': 5,
                'total_records_tested': int(column_row['total_columns']),
                'total_records_failed': int(column_row['failed_columns']),
                'date_range': f"{global_row['min_date']} to {global_row['max_date']}",
                'days_with_data': int(global_row['days_with_data'])
            }
            
            return metrics
        
        return {}
        
    except Exception as e:
        st.error(f"Error getting global metrics: {e}")
        return {}

def create_trend_analysis(df):
    """Create trend analysis over time"""
    if df.empty:
        return None, None
    
    try:
        # Daily trend - melt the score columns for analysis
        score_columns = ['completeness_score', 'uniqueness_score', 'consistency_score', 'validity_score', 'accuracy_score']
        
        trend_data = []
        for _, row in df.iterrows():
            date = row['execution_timestamp'].date()
            for col in score_columns:
                if pd.notna(row[col]):
                    dimension = col.replace('_score', '')
                    trend_data.append({
                        'execution_timestamp': date,
                        'dq_dimension': dimension,
                        'dq_score': row[col],
                        'table_name': row['table_name'],
                        'column_name': row['column_name']
                    })
        
        if not trend_data:
            return None, None
        
        daily_trend = pd.DataFrame(trend_data)
        daily_trend = daily_trend.groupby(['execution_timestamp', 'dq_dimension']).agg({
            'dq_score': 'mean'
        }).reset_index()
        
        # Create trend chart
        fig_trend = go.Figure()
        
        for dimension in daily_trend['dq_dimension'].unique():
            dim_data = daily_trend[daily_trend['dq_dimension'] == dimension]
            config = DQ_DIMENSIONS.get(dimension, {})
            
            fig_trend.add_trace(go.Scatter(
                x=dim_data['execution_timestamp'],
                y=dim_data['dq_score'],
                mode='lines+markers',
                name=config.get('name', dimension.title()),
                line=dict(color=config.get('color', '#667eea'), width=2),
                marker=dict(size=6),
                hovertemplate=f'<b>{config.get("name", dimension.title())}</b><br>Date: %{{x}}<br>Score: %{{y:.1f}}%<extra></extra>'
            ))
        
        fig_trend.update_layout(
            title='📈 Data Quality Score Trends',
            height=400,
            showlegend=True,
            hovermode='x unified',
            xaxis_title='Date',
            yaxis_title='DQ Score (%)'
        )
        
        # Create volume chart
        volume_data = df.groupby([df['execution_timestamp'].dt.date, 'domain']).agg({
            'column_name': 'count'
        }).reset_index()
        
        fig_volume = go.Figure()
        
        for domain in volume_data['domain'].unique():
            domain_data = volume_data[volume_data['domain'] == domain]
            
            fig_volume.add_trace(go.Bar(
                x=domain_data['execution_timestamp'],
                y=domain_data['column_name'],
                name=domain.upper(),
                hovertemplate=f'<b>{domain.upper()}</b><br>Date: %{{x}}<br>Columns Tested: %{{y}}<extra></extra>'
            ))
        
        fig_volume.update_layout(
            title='📊 Column Testing Volume',
            height=400,
            showlegend=True,
            hovermode='x unified',
            xaxis_title='Date',
            yaxis_title='Columns Tested',
            barmode='group'
        )
        
        return fig_trend, fig_volume
        
    except Exception as e:
        st.error(f"Error creating trend analysis: {e}")
        return None, None

def load_failing_records(start_date=None, end_date=None, domain_filter=None):
    """Load failing records from your dbt failing_records table"""
    try:
        base_query = """
        SELECT 
            domain,
            table_name,
            column_name,
            dimension,
            check_type,
            test_description,
            column_value,
            record,
            COUNT(*) as failure_count
        FROM failing_records
        WHERE 1=1
        """
        
        params = []
        
        # Add date filters (assuming failing_records has execution_timestamp)
        # If your failing_records table doesn't have timestamp, remove this section
        if hasattr('failing_records', 'execution_timestamp'):
            if start_date and end_date:
                if start_date == end_date:
                    base_query += " AND DATE(execution_timestamp) = %s"
                    params.append(start_date)
                else:
                    base_query += " AND DATE(execution_timestamp) BETWEEN %s AND %s"
                    params.extend([start_date, end_date])
        
        # Add domain filter
        if domain_filter and isinstance(domain_filter, list) and len(domain_filter) > 0:
            placeholders = ','.join(['%s'] * len(domain_filter))
            base_query += f" AND domain IN ({placeholders})"
            params.extend(domain_filter)
        
        base_query += """
        GROUP BY domain, table_name, column_name, dimension, check_type, test_description, column_value, record
        ORDER BY failure_count DESC, domain, table_name, column_name
        """
        
        df = db.run_query_with_params(base_query, tuple(params)) if params else db.run_query(base_query)
        
        return df
        
    except Exception as e:
        st.error(f"Error loading failing records: {e}")
        return pd.DataFrame()

def create_failing_records_summary(failing_records_df):
    """Create summary statistics for failing records"""
    if failing_records_df.empty:
        return {}
    
    summary = {
        'total_failures': int(failing_records_df['failure_count'].sum()),
        'affected_tables': failing_records_df['table_name'].nunique(),
        'affected_columns': failing_records_df['column_name'].nunique(),
        'most_common_failure': failing_records_df.loc[failing_records_df['failure_count'].idxmax()]['check_type'],
        'domains_affected': failing_records_df['domain'].nunique(),
        'failure_by_dimension': failing_records_df.groupby('dimension')['failure_count'].sum().to_dict(),
        'failure_by_domain': failing_records_df.groupby('domain')['failure_count'].sum().to_dict()
    }
    
    return summary
def run():
    """Data Quality Analytics Dashboard - DBT KPI Integration"""
    
    # Authentication check
    if st.session_state.get("allow_access", 0) != 1:
        st.error("🔒 Please log in to access this page")
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

    .professional-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
    }

    .professional-header h1 {
        font-size: 3rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }

    .professional-header p {
        font-size: 1.2rem;
        margin-bottom: 0.5rem;
        opacity: 0.9;
    }

    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
        margin-bottom: 1rem;
    }

    .section-header {
        background: linear-gradient(90deg, #f8fafc, #e2e8f0);
        padding: 1rem 1.5rem;
        border-radius: 8px;
        margin: 2rem 0 1rem 0;
        border-left: 4px solid #667eea;
        font-weight: 600;
        color: #1e293b;
    }

    .dimension-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        border-top: 4px solid;
        margin-bottom: 1rem;
        transition: transform 0.2s ease;
    }

    .dimension-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(0,0,0,0.15);
    }
    </style>
    """, unsafe_allow_html=True)

    # Header with user info
    st.markdown(f"""
    <div class="professional-header">
        <h1>🎯 Data Quality Analytics</h1>
        <p>Advanced Dimensional Framework • Real-Time Insights • Interactive Analytics</p>
        <p style="font-size: 0.9rem; opacity: 0.8;">
            User: {current_user} | Access: {'Administrator' if is_admin else ', '.join(user_domains)}
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Log page access
    log_user_action('page_access', {'page': 'analytics_dbt'}, current_user)

    # Enhanced Filters - Updated to match V2 style
    st.markdown("### 🔧 **Analysis Controls**")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        days_back = st.selectbox(
            "📅 Time Period",
            [1, 7, 14, 30, 90],
            index=1,  # Default to 7 days for analytics
            format_func=lambda x: "Today" if x == 1 else f"Last {x} days",
            key="analytics_date_range"
        )

    with col2:
        if days_back == 1:
            st.info("📊 Showing **today's** data quality results")
        else:
            st.info(f"📊 Showing data for the **last {days_back} days**")

    with col3:
        # Get available domains from database - update query for your tables
        try:
            domain_query = """
            SELECT DISTINCT domain 
            FROM column_kpi 
            WHERE execution_timestamp >= CURRENT_DATE - INTERVAL 30 DAY
            ORDER BY domain
            """
            domain_df = db.run_query(domain_query)
            available_domains = domain_df['domain'].tolist() if not domain_df.empty else []
        except:
            available_domains = ['hr', 'sales']  # Fallback to your known domains
        
        # Multi-select domain filter
        selected_domains = st.multiselect(
            "🏢 Domain",
            options=available_domains,
            default=available_domains if is_admin else [d for d in user_domains if d in available_domains],
            key="domain_filter",
            help="Select one or more domains to filter by"
        )
        
        if selected_domains:
            if len(selected_domains) == len(available_domains):
                st.caption("✅ All domains selected")
            else:
                st.caption(f"📊 {len(selected_domains)} of {len(available_domains)} domains selected")
        else:
            st.caption("⚠️ No domains selected - no data will be shown")

    with col4:
        dimension_filter = st.selectbox(
            "🎯 DQ Dimension",
            ["All"] + list(DQ_DIMENSIONS.keys()),
            key="dimension_filter"
        )

    with col5:
        if st.button("🔄 Refresh Data", key="refresh_analytics"):
            st.rerun()

    # Calculate start and end dates based on selection (matching your current logic)
    if days_back == 1:
        start_date = datetime.now().date()
        end_date = datetime.now().date()
    else:
        start_date = datetime.now().date() - timedelta(days=days_back)
        end_date = datetime.now().date()

    # Load filtered data with the new date logic
    kpi_results = load_kpi_results(
        start_date=start_date,
        end_date=end_date,
        dimension_filter=dimension_filter if dimension_filter != "All" else None,  # ADD THIS LINE
        domain_filter=selected_domains if selected_domains else None
    )

    if kpi_results.empty:
        st.warning("⚠️ No KPI results found for the selected filters.")
        return

    # Get global metrics
    global_metrics = get_global_dq_metrics(
        start_date=start_date,
        end_date=end_date,
        domain_filter=selected_domains if selected_domains else None
    )

    if global_metrics:
        # Global Metrics Overview - corrected to match home page logic
        st.markdown("### 🌍 **Global Data Quality Overview**")
        st.info("💡 **Dynamic Computation**: These metrics are computed in real-time from your dbt KPI tables.")

        # Calculate metrics using your DBT table structure
        if kpi_results.empty:
            st.warning("⚠️ No KPI results found for the selected filters.")
            return

        # Get the latest table scores for pass rate calculation (YOUR ORIGINAL WORKING CODE)
        latest_table_scores = kpi_results.groupby(['domain', 'table_name'])['table_score'].last().reset_index()

        # Calculate pass rate based on tables (like home page)
        total_tables = len(latest_table_scores)
        passing_tables = len(latest_table_scores[latest_table_scores['table_score'] >= 80])
        pass_rate = (passing_tables / total_tables * 100) if total_tables > 0 else 0

        # GET DIMENSIONS FROM TEST METADATA - REPLACE THE OLD DIMENSION COUNTING CODE HERE
        if selected_domains:
            metadata_query = f"""
            SELECT details
            FROM dq_test_metadata 
            WHERE level = 'column' 
            AND domain IN ({','.join(['%s'] * len(selected_domains))})
            AND details IS NOT NULL
            """
            
            details_df = db.run_query_with_params(metadata_query, tuple(selected_domains))
            
            # Extract unique dimensions from all details
            unique_dimensions = set()
            for details in details_df['details']:
                checks = details.split(',')
                for check in checks:
                    check = check.strip()
                    if check in ['null', 'threshold']:
                        unique_dimensions.add('completeness')
                    elif check == 'uniqueness':
                        unique_dimensions.add('uniqueness') 
                    elif check == 'consistency':
                        unique_dimensions.add('consistency')
                    elif check in ['validity', 'domain', 'regex']:
                        unique_dimensions.add('validity')
                    elif check == 'accuracy':
                        unique_dimensions.add('accuracy')
            
            dimensions_covered = len(unique_dimensions)
        else:
            dimensions_covered = 0

        # Calculate other metrics
        total_columns = len(kpi_results)
        avg_score = kpi_results['column_score'].mean()
        
        # Critical failures - columns with score < 60
        critical_failures = len(kpi_results[(kpi_results['column_score'] < 60) & (kpi_results['column_score'].notna())])
        
        unique_domains = kpi_results['domain'].nunique()

        col1, col2, col3, col4 = st.columns(4)
        # ... rest of your metrics display code

        with col1:
            st.metric(
                "Overall Pass Rate", 
                f"{pass_rate:.1f}%",
                delta=f"{passing_tables}/{total_tables} tables"
            )

        with col2:
            st.metric(
                "Average DQ Score", 
                f"{avg_score:.1f}%",
                delta=f"{total_tables} tables tested"
            )

        with col3:
            st.metric(
                "Domains Covered", 
                f"{unique_domains}",
                delta=f"{dimensions_covered} dimensions"  # Dynamic based on selected domains
            )

        with col4:
            st.metric(
                "Critical Issues", 
                f"{critical_failures}",
                delta="Scores < 60%" if critical_failures > 0 else "No critical issues"
            )

    st.markdown("---")

    # Dimensional Overview
    st.markdown("### 🎯 **Data Quality Dimensional Analysis**")

    # Create filtered dimensional summary based on current filters
    filtered_dimensional_summary = create_dimensional_summary(
        start_date=start_date,
        end_date=end_date,
        dimension_filter=dimension_filter if dimension_filter != "All" else None,
        domain_filter=selected_domains if selected_domains else None
    )

    if not filtered_dimensional_summary.empty:
        # Create interactive radar chart with filtered data
        if not filtered_dimensional_summary.empty:
            # Prepare radar chart data
            dimensions = filtered_dimensional_summary['dq_dimension'].tolist()
            scores = filtered_dimensional_summary['overall_score'].fillna(0).tolist()
            
            # Create radar chart using HTML component
            radar_data = {
                "data": [{
                    "type": "scatterpolar",
                    "r": scores,
                    "theta": [DQ_DIMENSIONS.get(dim, {}).get('name', dim.title()) for dim in dimensions],
                    "fill": "toself",
                    "name": "DQ Scores",
                    "line": {"color": "rgb(59, 130, 246)"},
                    "fillcolor": "rgba(59, 130, 246, 0.3)",
                    "hovertemplate": "<b>%{theta}</b><br>Score: %{r:.1f}%<extra></extra>"
                }],
                "layout": {
                    "polar": {
                        "radialaxis": {
                            "visible": True,
                            "range": [0, 100],
                            "tickmode": "linear",
                            "tick0": 0,
                            "dtick": 20,
                            "tickformat": ".0f",
                            "ticksuffix": "%"
                        }
                    },
                    "showlegend": True,
                    "title": "🎯 Data Quality Dimensional Overview",
                    "hovermode": "closest"
                }
            }
            
            create_interactive_chart(radar_data, height=500)
        
        # Dimensional cards with filtered data
        cols = st.columns(3)
        for idx, (_, row) in enumerate(filtered_dimensional_summary.iterrows()):
            with cols[idx % 3]:
                dimension = row['dq_dimension']
                config = DQ_DIMENSIONS.get(dimension, {})
                
                st.markdown(f"""
                <div class="dimension-card" style="border-top-color: {config.get('color', '#667eea')};">
                    <h4 style="color: {config.get('color', '#667eea')}; margin-bottom: 1rem;">
                        {config.get('icon', '📊')} {config.get('name', dimension.title())}
                    </h4>
                    <p style="font-size: 0.9rem; color: #64748b; margin-bottom: 1rem;">
                        {config.get('description', 'Data quality dimension')}
                    </p>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                        <span>Score:</span>
                        <strong style="color: {config.get('color', '#667eea')};">{row['overall_score']:.1f}%</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                        <span>Columns:</span>
                        <strong>{row['total_tests']}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span>Pass Rate:</span>
                        <strong style="color: {'#10b981' if row['pass_rate'] > 0.8 else '#f59e0b' if row['pass_rate'] > 0.6 else '#ef4444'};">
                            {row['pass_rate']:.1%}
                        </strong>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No dimensional data available for the selected filters.")

    st.markdown("---")

    # Key Metrics Overview
    st.markdown("### 📊 **Key Performance Indicators**")

    # Show what dimension is being analyzed
    if dimension_filter and dimension_filter != "All":
        st.info(f"💡 **Dimension Focus**: Showing metrics for {DQ_DIMENSIONS.get(dimension_filter, {}).get('name', dimension_filter.title())} dimension only")
    else:
        st.info("💡 **Latest Run Data**: The metrics below show data from the most recent test execution for each test, providing current quality status.")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        if dimension_filter and dimension_filter != "All":
            # Count only columns that have data for the selected dimension
            dimension_column = f"{dimension_filter.lower()}_score"
            total_columns = len(kpi_results[kpi_results[dimension_column].notna()])
            st.metric("Columns Tested", f"{total_columns:,}", delta=f"For {dimension_filter.title()}")
        else:
            total_columns = len(kpi_results)
            st.metric("Total Columns", f"{total_columns:,}")

    with col2:
        if dimension_filter and dimension_filter != "All":
            # Calculate pass rate for the specific dimension
            dimension_column = f"{dimension_filter.lower()}_score"
            dimension_data = kpi_results[kpi_results[dimension_column].notna()]
            if not dimension_data.empty:
                pass_rate = (dimension_data[dimension_column] >= 80).mean()
                st.metric("Dimension Pass Rate", f"{pass_rate:.1%}", delta=f"{dimension_filter.title()} only")
            else:
                st.metric("Dimension Pass Rate", "No Data", delta="No tests found")
        else:
            # Overall pass rate from column scores
            pass_rate = (kpi_results['column_score'] >= 80).mean()
            st.metric("Overall Pass Rate", f"{pass_rate:.1%}")

    with col3:
        if dimension_filter and dimension_filter != "All":
            # Average score for the specific dimension
            dimension_column = f"{dimension_filter.lower()}_score"
            dimension_data = kpi_results[kpi_results[dimension_column].notna()]
            if not dimension_data.empty:
                avg_score = dimension_data[dimension_column].mean()
                st.metric("Avg Dimension Score", f"{avg_score:.1f}%", delta=f"{dimension_filter.title()}")
            else:
                st.metric("Avg Dimension Score", "No Data")
        else:
            avg_score = kpi_results['column_score'].mean()
            st.metric("Average DQ Score", f"{avg_score:.1f}%")

    with col4:
        # Tables monitored - this stays the same regardless of dimension
        unique_tables = kpi_results[['domain', 'table_name']].drop_duplicates()
        if dimension_filter and dimension_filter != "All":
            st.metric("Tables with Dimension", f"{len(unique_tables):,}", delta=f"Testing {dimension_filter.title()}")
        else:
            st.metric("Tables Monitored", f"{len(unique_tables):,}")

    with col5:
        if dimension_filter and dimension_filter != "All":
            # Failing columns for the specific dimension
            dimension_column = f"{dimension_filter.lower()}_score"
            dimension_data = kpi_results[kpi_results[dimension_column].notna()]
            if not dimension_data.empty:
                failing_columns = len(dimension_data[dimension_data[dimension_column] < 80])
                st.metric("Failing in Dimension", f"{failing_columns:,}", delta=f"{dimension_filter.title()} < 80%")
            else:
                st.metric("Failing in Dimension", "No Data")
        else:
            failing_columns = len(kpi_results[kpi_results['column_score'] < 80])
            st.metric("Failing Columns", f"{failing_columns:,}")

    # Trend Analysis
    st.markdown("### 📈 **Trend Analysis**")

    # Show what's being analyzed
    if dimension_filter and dimension_filter != "All":
        st.info(f"📊 **Dimension Focus**: Trend analysis for {DQ_DIMENSIONS.get(dimension_filter, {}).get('name', dimension_filter.title())} dimension")
    else:
        st.info("📊 **Comprehensive Analysis**: Showing trends across all dimensions")

    # Create interactive trend analysis
    if not kpi_results.empty:
        if dimension_filter and dimension_filter != "All":
            # Single dimension analysis
            dimension_column = f"{dimension_filter.lower()}_score"
            
            # Filter data to only include rows with data for the selected dimension
            filtered_data = kpi_results[kpi_results[dimension_column].notna()].copy()
            
            if not filtered_data.empty:
                # Prepare trend data for single dimension
                daily_trend = filtered_data.groupby([filtered_data['execution_timestamp'].dt.date, 'domain']).agg({
                    dimension_column: 'mean'
                }).reset_index()
                daily_trend.columns = ['execution_timestamp', 'domain', 'dq_score']
                daily_trend['dq_dimension'] = dimension_filter.lower()
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**📈 {dimension_filter.title()} Score Trends**")
                    create_scatter_chart(
                        df=daily_trend,
                        x_col="execution_timestamp",
                        y_col="dq_score",
                        color_col="domain",
                        title=f"{dimension_filter.title()} Score Trends by Domain",
                        height=400
                    )
                
                with col2:
                    st.markdown(f"**📊 {dimension_filter.title()} Testing Volume**")
                    volume_data = filtered_data.groupby(['domain', filtered_data['execution_timestamp'].dt.date]).size().reset_index()
                    volume_data.columns = ['domain', 'date', 'count']
                    
                    volume_chart_data = {
                        "data": [],
                        "layout": {
                            "title": f"{dimension_filter.title()} Testing Volume",
                            "xaxis": {"title": "Date"},
                            "yaxis": {"title": "Columns Tested"},
                            "barmode": "group"
                        }
                    }
                    
                    for domain in volume_data['domain'].unique():
                        domain_data = volume_data[volume_data['domain'] == domain]
                        volume_chart_data["data"].append({
                            "x": [d.strftime('%Y-%m-%d') for d in domain_data['date']],
                            "y": domain_data['count'].tolist(),
                            "type": "bar",
                            "name": domain.upper(),
                            "hovertemplate": f"<b>{domain.upper()}</b><br>Date: %{{x}}<br>Columns: %{{y}}<extra></extra>"
                        })
                    
                    create_interactive_chart(volume_chart_data, height=400)
            else:
                st.warning(f"⚠️ No data available for {dimension_filter.title()} dimension in the selected time period.")
        
        else:
            # Multi-dimension analysis (original code)
            score_columns = ['completeness_score', 'uniqueness_score', 'consistency_score', 'validity_score', 'accuracy_score']
            
            trend_data = []
            for _, row in kpi_results.iterrows():
                date = row['execution_timestamp'].date()
                for col in score_columns:
                    if pd.notna(row[col]):
                        dimension = col.replace('_score', '')
                        trend_data.append({
                            'execution_timestamp': date,
                            'dq_dimension': dimension,
                            'dq_score': row[col],
                            'domain': row['domain']
                        })
            
            if trend_data:
                daily_trend = pd.DataFrame(trend_data)
                daily_trend = daily_trend.groupby(['execution_timestamp', 'dq_dimension']).agg({
                    'dq_score': 'mean'
                }).reset_index()
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**📈 DQ Score Trends by Dimension**")
                    create_scatter_chart(
                        df=daily_trend,
                        x_col="execution_timestamp",
                        y_col="dq_score",
                        color_col="dq_dimension",
                        title="DQ Score Trends by Dimension",
                        height=400
                    )
                
                with col2:
                    st.markdown("**📊 Overall Testing Volume**")
                    volume_data = kpi_results.groupby(['domain', kpi_results['execution_timestamp'].dt.date]).size().reset_index()
                    volume_data.columns = ['domain', 'date', 'count']
                    
                    volume_chart_data = {
                        "data": [],
                        "layout": {
                            "title": "Column Testing Volume",
                            "xaxis": {"title": "Date"},
                            "yaxis": {"title": "Columns Tested"},
                            "barmode": "group"
                        }
                    }
                    
                    for domain in volume_data['domain'].unique():
                        domain_data = volume_data[volume_data['domain'] == domain]
                        volume_chart_data["data"].append({
                            "x": [d.strftime('%Y-%m-%d') for d in domain_data['date']],
                            "y": domain_data['count'].tolist(),
                            "type": "bar",
                            "name": domain.upper(),
                            "hovertemplate": f"<b>{domain.upper()}</b><br>Date: %{{x}}<br>Columns: %{{y}}<extra></extra>"
                        })
                    
                    create_interactive_chart(volume_chart_data, height=400)

    st.markdown("---")

    # Advanced Visualizations Section
    st.markdown("### 📊 **Advanced Data Visualizations**")

    # Show what's being analyzed
    if dimension_filter and dimension_filter != "All":
        st.info(f"📊 **Dimension Focus**: Advanced visualizations for {DQ_DIMENSIONS.get(dimension_filter, {}).get('name', dimension_filter.title())} dimension")
    else:
        st.info("📊 **Comprehensive Analysis**: Advanced visualizations across all dimensions")

    # Time Series Analysis
    st.markdown("#### 📈 **Time Series Analysis**")

    # Create time series chart
    if not kpi_results.empty:
        if dimension_filter and dimension_filter != "All":
            # Single dimension time series
            dimension_column = f"{dimension_filter.lower()}_score"
            filtered_data = kpi_results[kpi_results[dimension_column].notna()].copy()
            
            if not filtered_data.empty:
                # Prepare time series data for single dimension
                time_series_data = filtered_data.groupby([filtered_data['execution_timestamp'].dt.date, 'domain']).agg({
                    dimension_column: 'mean'
                }).reset_index()
                time_series_data.columns = ['execution_timestamp', 'domain', 'avg_dimension_score']
                
                # Use scatter chart for time series by domain
                create_scatter_chart(
                    df=time_series_data,
                    x_col="execution_timestamp",
                    y_col="avg_dimension_score",
                    color_col="domain",
                    title=f"📈 {dimension_filter.title()} Scores Over Time by Domain",
                    height=500
                )
            else:
                st.warning(f"⚠️ No time series data available for {dimension_filter.title()} dimension")
        
        else:
            # Multi-dimension time series (original code)
            time_series_data = kpi_results.groupby([kpi_results['execution_timestamp'].dt.date, 'domain']).agg({
                'column_score': 'mean',
                'completeness_score': 'mean',
                'uniqueness_score': 'mean',
                'consistency_score': 'mean',
                'validity_score': 'mean',
                'accuracy_score': 'mean'
            }).reset_index()
            time_series_data.columns = ['execution_timestamp', 'domain', 'avg_column_score', 'avg_completeness', 'avg_uniqueness', 'avg_consistency', 'avg_validity', 'avg_accuracy']
            
            # Use scatter chart for time series by domain
            create_scatter_chart(
                df=time_series_data,
                x_col="execution_timestamp",
                y_col="avg_column_score",
                color_col="domain",
                title="📈 Data Quality Scores Over Time by Domain",
                height=500
            )

    # Heatmap Analysis
    st.markdown("#### 🔥 **Quality Heatmap by Domain & Dimension**")

    if not kpi_results.empty:
        if dimension_filter and dimension_filter != "All":
            # Single dimension heatmap (by domain only)
            dimension_column = f"{dimension_filter.lower()}_score"
            filtered_data = kpi_results[kpi_results[dimension_column].notna()]
            
            if not filtered_data.empty:
                # Create domain performance chart for single dimension
                domain_perf = filtered_data.groupby('domain')[dimension_column].mean().reset_index()
                domain_perf.columns = ['domain', 'avg_score']
                
                heatmap_chart_data = {
                    "data": [{
                        "x": domain_perf['domain'].tolist(),
                        "y": [dimension_filter.title()],
                        "z": [domain_perf['avg_score'].tolist()],
                        "type": "heatmap",
                        "colorscale": [
                            [0.0, 'rgb(220, 38, 38)'],    # Red for lowest quality (0%)
                            [0.5, 'rgb(234, 179, 8)'],    # Yellow for medium quality (50%)
                            [1.0, 'rgb(34, 197, 94)']     # Green for good quality (100%)
                        ],
                        "zmin": 0,
                        "zmax": 100,
                        "hovertemplate": f"<b>%{{x}} - {dimension_filter.title()}</b><br>Avg Score: %{{z:.1f}}%<extra></extra>",
                        "colorbar": {"title": "DQ Score (%)"}
                    }],
                    "layout": {
                        "title": f"🔥 {dimension_filter.title()} Quality by Domain",
                        "xaxis": {"title": "Domain"},
                        "yaxis": {"title": "Dimension"}
                    }
                }
                
                create_interactive_chart(heatmap_chart_data, height=400)
            else:
                st.warning(f"⚠️ No heatmap data available for {dimension_filter.title()} dimension")
        
        else:
            # Multi-dimension heatmap (original code)
            heatmap_data = []
            dimension_cols = ['completeness_score', 'uniqueness_score', 'consistency_score', 'validity_score', 'accuracy_score']
            
            for _, row in kpi_results.iterrows():
                for dim_col in dimension_cols:
                    if pd.notna(row[dim_col]):
                        dimension = dim_col.replace('_score', '')
                        heatmap_data.append({
                            'domain': row['domain'],
                            'dq_dimension': dimension,
                            'score': row[dim_col]
                        })
            
            if heatmap_data:
                heatmap_df = pd.DataFrame(heatmap_data)
                heatmap_pivot = heatmap_df.groupby(['domain', 'dq_dimension'])['score'].mean().unstack()
                heatmap_filled = heatmap_pivot.fillna(-1)
                
                heatmap_chart_data = {
                    "data": [{
                        "z": heatmap_filled.values.tolist(),
                        "x": heatmap_filled.columns.tolist(),
                        "y": heatmap_filled.index.tolist(),
                        "type": "heatmap",
                        "colorscale": [
                            [0.0, 'rgb(128, 128, 128)'],   # Gray for "Not Tested" (-1 values)
                            [0.001, 'rgb(220, 38, 38)'],  # Red for lowest quality (0%)
                            [0.5, 'rgb(234, 179, 8)'],    # Yellow for medium quality (50%)
                            [1.0, 'rgb(34, 197, 94)']     # Green for good quality (100%)
                        ],
                        "zmin": -1,
                        "zmax": 100,
                        "hovertemplate": "<b>%{y} - %{x}</b><br>Score: %{customdata}<extra></extra>",
                        "customdata": [
                            [f"{score:.1f}%" if score >= 0 else "Not Tested" 
                            for score in row] 
                            for row in heatmap_filled.values
                        ],
                        "colorbar": {
                            "title": "DQ Score (%)",
                            "tickvals": [-1, 0, 25, 50, 75, 100],
                            "ticktext": ["Not Tested", "0%", "25%", "50%", "75%", "100%"]
                        }
                    }],
                    "layout": {
                        "title": "🔥 Data Quality Heatmap (Only Tested Dimensions)",
                        "xaxis": {"title": "DQ Dimension"},
                        "yaxis": {"title": "Domain"},
                        "height": 400
                    }
                }
                
                create_interactive_chart(heatmap_chart_data, height=400)

    # Performance Distribution
    st.markdown("#### 📊 **Performance Distribution Analysis**")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**📦 Score Distribution by Domain**")
        if not kpi_results.empty:
            if dimension_filter and dimension_filter != "All":
                # Single dimension distribution
                dimension_column = f"{dimension_filter.lower()}_score"
                filtered_data = kpi_results[kpi_results[dimension_column].notna()]
                
                if not filtered_data.empty:
                    create_box_chart(
                        df=filtered_data,
                        y_col=dimension_column,
                        group_col="domain",
                        title=f"📦 {dimension_filter.title()} Score Distribution by Domain",
                        height=400
                    )
                else:
                    st.warning(f"⚠️ No distribution data for {dimension_filter.title()}")
            else:
                # Overall distribution
                create_box_chart(
                    df=kpi_results,
                    y_col="column_score",
                    group_col="domain",
                    title="📦 Score Distribution by Domain",
                    height=400
                )

    with col2:
        if dimension_filter and dimension_filter != "All":
            st.markdown(f"**📊 {dimension_filter.title()} Performance Details**")
            dimension_column = f"{dimension_filter.lower()}_score"
            filtered_data = kpi_results[kpi_results[dimension_column].notna()]
            
            if not filtered_data.empty:
                # Single dimension performance summary
                dim_config = DQ_DIMENSIONS.get(dimension_filter, {})
                avg_score = filtered_data[dimension_column].mean()
                std_score = filtered_data[dimension_column].std()
                test_count = len(filtered_data)
                pass_rate = (filtered_data[dimension_column] >= 80).mean()
                
                perf_data = {
                    "data": [{
                        "x": [dim_config.get('name', dimension_filter.title())],
                        "y": [avg_score],
                        "type": "bar",
                        "name": "Average Score",
                        "marker": {
                            "color": [dim_config.get('color', '#667eea')],
                            "opacity": 0.8
                        },
                        "error_y": {
                            "type": "data",
                            "array": [std_score],
                            "visible": True
                        },
                        "hovertemplate": (
                            f"<b>{dim_config.get('name', dimension_filter.title())}</b><br>" +
                            "Avg Score: %{y:.1f}%<br>" +
                            f"Std Dev: {std_score:.1f}<br>" +
                            f"Tests: {test_count}<br>" +
                            f"Pass Rate: {pass_rate:.1%}<br>" +
                            "<extra></extra>"
                        )
                    }],
                    "layout": {
                        "title": f"📊 {dimension_filter.title()} Performance Summary",
                        "xaxis": {"title": "Data Quality Dimension"},
                        "yaxis": {"title": "Average Score (%)"},
                        "showlegend": False
                    }
                }
                
                create_interactive_chart(perf_data, height=400)
            else:
                st.warning(f"⚠️ No performance data for {dimension_filter.title()}")
        
        else:
            st.markdown("**📊 Dimensional Performance Summary**")
            # Multi-dimension performance summary (original code)
            dim_summary_data = []
            dimension_cols = ['completeness_score', 'uniqueness_score', 'consistency_score', 'validity_score', 'accuracy_score']
            
            for dim_col in dimension_cols:
                dimension = dim_col.replace('_score', '')
                dim_data = kpi_results[kpi_results[dim_col].notna()]
                if not dim_data.empty:
                    avg_score = dim_data[dim_col].mean()
                    std_score = dim_data[dim_col].std()
                    test_count = len(dim_data)
                    pass_rate = (dim_data[dim_col] >= 80).mean()
                    
                    dim_summary_data.append({
                        'dq_dimension': dimension,
                        'avg_score': avg_score,
                        'std_score': std_score,
                        'test_count': test_count,
                        'pass_rate': pass_rate
                    })
            
            if dim_summary_data:
                dim_summary_df = pd.DataFrame(dim_summary_data)
                
                perf_data = {
                    "data": [{
                        "x": [DQ_DIMENSIONS.get(dim, {}).get('name', dim.title()) for dim in dim_summary_df['dq_dimension']],
                        "y": dim_summary_df['avg_score'].tolist(),
                        "type": "bar",
                        "name": "Average Score",
                        "marker": {
                            "color": [DQ_DIMENSIONS.get(dim, {}).get('color', '#667eea') for dim in dim_summary_df['dq_dimension']],
                            "opacity": 0.8
                        },
                        "error_y": {
                            "type": "data",
                            "array": dim_summary_df['std_score'].tolist(),
                            "visible": True
                        },
                        "hovertemplate": (
                            "<b>%{x}</b><br>" +
                            "Avg Score: %{y:.1f}%<br>" +
                            "Std Dev: %{error_y.array:.1f}<br>" +
                            "Tests: %{customdata[0]}<br>" +
                            "Pass Rate: %{customdata[1]:.1%}<br>" +
                            "<extra></extra>"
                        ),
                        "customdata": list(zip(dim_summary_df['test_count'], dim_summary_df['pass_rate']))
                    }],
                    "layout": {
                        "title": "📊 Dimensional Performance Summary",
                        "xaxis": {"title": "Data Quality Dimension"},
                        "yaxis": {"title": "Average Score (%)"},
                        "showlegend": False
                    }
                }
                
                create_interactive_chart(perf_data, height=400)

    st.markdown("---")

    # Additional Performance Analysis
    st.markdown("#### 🎯 **Advanced Performance Metrics**")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**📈 Table Performance Ranking**")
        if not kpi_results.empty:
            # Calculate table performance metrics
            table_performance = kpi_results.groupby(['domain', 'table_name']).agg({
                'column_score': ['mean', 'count', 'std'],
                'table_score': 'first'  # Get the table score
            }).round(2)
            
            table_performance.columns = ['avg_column_score', 'column_count', 'score_std', 'table_score']
            table_performance = table_performance.reset_index()
            table_performance['table_full_name'] = table_performance['domain'] + '.' + table_performance['table_name']
            
            # Sort by table score (more accurate than average column score)
            table_performance = table_performance.sort_values('table_score', ascending=False)
            
            # Create horizontal bar chart for top 10 tables
            top_tables = table_performance.head(10)
            
            ranking_data = {
                "data": [{
                    "x": top_tables['table_score'].tolist(),
                    "y": top_tables['table_full_name'].tolist(),
                    "type": "bar",
                    "orientation": "h",
                    "name": "Table Score",
                    "marker": {
                        "color": top_tables['table_score'].tolist(),
                        "colorscale": [
                            [0, 'rgb(220, 38, 38)'],
                            [0.8, 'rgb(234, 179, 8)'],
                            [1, 'rgb(34, 197, 94)']
                        ],
                        "cmin": 0,
                        "cmax": 100
                    },
                    "hovertemplate": "<b>%{y}</b><br>Table Score: %{x:.1f}%<br>Columns: %{customdata}<extra></extra>",
                    "customdata": top_tables['column_count'].tolist()
                }],
                "layout": {
                    "title": "🏆 Top Performing Tables",
                    "xaxis": {"title": "Table Score (%)"},
                    "yaxis": {"title": "Table"},
                    "margin": {"l": 200},
                    "height": 400
                }
            }
            
            create_interactive_chart(ranking_data, height=400)

    with col2:
        st.markdown("**📊 Score Distribution Summary**")
        if not kpi_results.empty:
            # Create score range analysis
            score_ranges = {
                'Excellent (90-100%)': len(kpi_results[kpi_results['column_score'] >= 90]),
                'Good (80-89%)': len(kpi_results[(kpi_results['column_score'] >= 80) & (kpi_results['column_score'] < 90)]),
                'Fair (70-79%)': len(kpi_results[(kpi_results['column_score'] >= 70) & (kpi_results['column_score'] < 80)]),
                'Poor (60-69%)': len(kpi_results[(kpi_results['column_score'] >= 60) & (kpi_results['column_score'] < 70)]),
                'Critical (<60%)': len(kpi_results[kpi_results['column_score'] < 60])
            }
            
            # Create pie chart for score distribution
            pie_data = {
                "data": [{
                    "labels": list(score_ranges.keys()),
                    "values": list(score_ranges.values()),
                    "type": "pie",
                    "marker": {
                        "colors": ['#10b981', '#22c55e', '#eab308', '#f97316', '#ef4444']
                    },
                    "hovertemplate": "<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>",
                    "textinfo": "label+percent",
                    "textposition": "auto"
                }],
                "layout": {
                    "title": "📊 Column Score Distribution",
                    "height": 400,
                    "showlegend": True,
                    "legend": {"orientation": "v", "x": 1.05, "y": 1}
                }
            }
            
            create_interactive_chart(pie_data, height=400)
            
            # Add summary statistics
            st.markdown("**📈 Summary Statistics:**")
            col_stats = kpi_results['column_score'].describe()
            st.write(f"• **Mean**: {col_stats['mean']:.1f}%")
            st.write(f"• **Median**: {col_stats['50%']:.1f}%")
            st.write(f"• **Std Dev**: {col_stats['std']:.1f}%")
            st.write(f"• **Min**: {col_stats['min']:.1f}%")
            st.write(f"• **Max**: {col_stats['max']:.1f}%")


    # Deep Dive Analysis with Instructions
    st.markdown("### 🔍 **Deep Dive Analysis - Failed Test Investigation**")

    # Instructions section for deep dive
    st.markdown("""
    <div style="background: #fef2f2; border: 1px solid #fca5a5; border-radius: 8px; padding: 1.5rem; margin-bottom: 2rem;">
        <h4 style="color: #991b1b; margin: 0 0 1rem 0;">🔍 Deep Dive Investigation Instructions</h4>
        <div style="color: #7f1d1d; line-height: 1.6;">
            <p><strong>🎯 How to Investigate Any Tests:</strong></p>
            <ul style="margin: 0.5rem 0; padding-left: 1.5rem;">
                <li><strong>Select Any Tests:</strong> In the table below, check the boxes next to tests you want to investigate (both passed and failed)</li>
                <li><strong>Submit Selection:</strong> Click the "🔍 Investigate Selected Tests" button to get detailed analysis</li>
                <li><strong>Review Results:</strong> For failed tests, see the actual failing data records with highlighted columns</li>
                <li><strong>Check Passed Tests:</strong> For passed tests, see confirmation that no failing records were found</li>
                <li><strong>Download Results:</strong> Export the analysis for further investigation</li>
            </ul>
            <p><strong>💡 Tips for Effective Investigation:</strong></p>
            <ul style="margin: 0.5rem 0; padding-left: 1.5rem;">
                <li>Focus on <strong>high-impact failures</strong> (critical severity, high business impact)</li>
                <li>Look for <strong>patterns</strong> in failed records (common values, time periods)</li>
                <li>Investigate <strong>multiple failures</strong> in the same table or domain</li>
                <li>Use the <strong>error messages</strong> to understand root causes</li>
            </ul>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Advanced Data Explorer
    st.markdown("#### 📋 **Detailed Data Explorer**")

    # Summary statistics
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### 📊 **Test Results Summary**")
        if not kpi_results.empty:
            # Create summary by dimension and pass/fail status
            summary_data = []
            dimension_cols = ['completeness_score', 'uniqueness_score', 'consistency_score', 'validity_score', 'accuracy_score']
            
            for dim_col in dimension_cols:
                dimension = dim_col.replace('_score', '')
                dim_data = kpi_results[kpi_results[dim_col].notna()]
                if not dim_data.empty:
                    total_tests = len(dim_data)
                    passed_tests = len(dim_data[dim_data[dim_col] >= 80])
                    failed_tests = total_tests - passed_tests
                    pass_rate = passed_tests / total_tests if total_tests > 0 else 0
                    
                    summary_data.append({
                        'Dimension': dimension.title(),
                        'Total': total_tests,
                        'Passed': passed_tests,
                        'Failed': failed_tests,
                        'Pass Rate': f"{pass_rate:.1%}"
                    })
            
            if summary_data:
                summary_df = pd.DataFrame(summary_data)
                st.dataframe(summary_df, use_container_width=True, hide_index=True)

    with col2:
        st.markdown("##### 🎯 **Performance by Domain**")
        if not kpi_results.empty:
            domain_stats = kpi_results.groupby('domain').agg({
                'column_score': 'mean',
                'table_score': 'first'  # Get table score
            }).round(1)
            domain_stats.columns = ['Avg Column Score', 'Table Score']
            
            # Add pass rate calculation
            pass_rates = []
            for domain in domain_stats.index:
                domain_data = kpi_results[kpi_results['domain'] == domain]
                pass_rate = (domain_data['column_score'] >= 80).mean()
                pass_rates.append(f"{pass_rate:.1%}")
            
            domain_stats['Pass Rate'] = pass_rates
            st.dataframe(domain_stats, use_container_width=True)

    # Interactive table with advanced features
    st.markdown("#### 🔍 **Test Results - Select Tests for Deep Dive**")

    # Show filter status
    failed_tests_count = len(kpi_results[kpi_results['column_score'] < 80]) if not kpi_results.empty else 0
    total_tests_count = len(kpi_results) if not kpi_results.empty else 0

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Tests", f"{total_tests_count:,}")
    with col2:
        st.metric("Failed Tests", f"{failed_tests_count:,}", delta=f"{failed_tests_count/total_tests_count*100:.1f}% of total" if total_tests_count > 0 else "0%")
    with col3:
        if failed_tests_count > 0:
            st.error(f"⚠️ {failed_tests_count} tests need investigation")
        else:
            st.success("✅ All tests passing!")

    if not kpi_results.empty:
        # Prepare display data - focus on the most important columns for investigation
        display_df = kpi_results[[
            'execution_timestamp', 'domain', 'table_name', 'column_name', 
            'column_score', 'completeness_score', 'uniqueness_score', 
            'consistency_score', 'validity_score', 'accuracy_score'
        ]].copy()

        # Format timestamp
        display_df['execution_timestamp'] = pd.to_datetime(display_df['execution_timestamp']).dt.strftime('%Y-%m-%d %H:%M')
        
        # Add status column
        display_df['status'] = display_df['column_score'].apply(lambda x: 'pass' if x >= 80 else 'fail')

        # Add selection capabilities
        grid_key = f"analytics_table_{'_'.join(selected_domains) if selected_domains else 'all'}"
        grid_response = create_advanced_table(display_df, key=grid_key)

        # Enhanced selection handling
        if grid_response and 'selected_rows' in grid_response:
            selected_rows = grid_response['selected_rows']
            
            if selected_rows is not None:
                if isinstance(selected_rows, pd.DataFrame):
                    has_selection = not selected_rows.empty
                    selected_count = len(selected_rows)
                elif isinstance(selected_rows, list):
                    has_selection = len(selected_rows) > 0
                    selected_count = len(selected_rows)
                else:
                    has_selection = False
                    selected_count = 0
            else:
                has_selection = False
                selected_count = 0

            if has_selection:
                st.info(f"📋 {selected_count} row(s) selected for investigation")
                
                # Convert to DataFrame once at the beginning
                if isinstance(selected_rows, pd.DataFrame):
                    selected_df = selected_rows
                else:
                    selected_df = pd.DataFrame(selected_rows)
                
                # Create action buttons
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    investigate_button = st.button("🔍 Investigate Selected Tests", key="investigate_tests", type="primary")
                
                with col2:
                    if st.button("📥 Export Selected Data", key="export_selected"):
                        if isinstance(selected_rows, pd.DataFrame):
                            selected_df = selected_rows
                        else:
                            selected_df = pd.DataFrame(selected_rows)
                        
                        # Load actual failing records from your failing_records table
                        all_failing_records_export = []
                        
                        for _, row in selected_df.iterrows():
                            domain = row.get('domain', '')
                            table_name = row.get('table_name', '')
                            column_name = row.get('column_name', '')
                            execution_timestamp = row.get('execution_timestamp', '')
                            
                            # Query actual failing records for this specific test
                            try:
                                failing_query = """
                                SELECT domain, table_name, column_name, dimension, check_type, 
                                    test_description, column_value, record
                                FROM failing_records
                                WHERE domain = %s AND table_name = %s AND column_name = %s
                                """
                                
                                failing_records = db.run_query_with_params(failing_query, (domain, table_name, column_name))
                                
                                if not failing_records.empty:
                                    # Add test context to each failing record
                                    for _, fail_record in failing_records.iterrows():
                                        export_record = {
                                            'test_execution_timestamp': execution_timestamp,
                                            'test_domain': domain,
                                            'test_table': table_name,
                                            'test_column': column_name,
                                            'test_overall_score': row.get('column_score', 0),
                                            'test_status': row.get('status', 'unknown'),
                                            'failure_dimension': fail_record['dimension'],
                                            'failure_check_type': fail_record['check_type'],
                                            'failure_description': fail_record['test_description'],
                                            'failing_column_value': fail_record['column_value'],
                                            'complete_failing_record': fail_record['record']
                                        }
                                        all_failing_records_export.append(export_record)
                                else:
                                    # No failing records found (test passed)
                                    export_record = {
                                        'test_execution_timestamp': execution_timestamp,
                                        'test_domain': domain,
                                        'test_table': table_name,
                                        'test_column': column_name,
                                        'test_overall_score': row.get('column_score', 0),
                                        'test_status': row.get('status', 'unknown'),
                                        'failure_dimension': 'None',
                                        'failure_check_type': 'N/A - Test Passed',
                                        'failure_description': 'No failing records found',
                                        'failing_column_value': 'N/A',
                                        'complete_failing_record': 'N/A'
                                    }
                                    all_failing_records_export.append(export_record)
                                    
                            except Exception as e:
                                st.error(f"Error loading failing records for {domain}.{table_name}.{column_name}: {e}")
                        
                        if all_failing_records_export:
                            export_df = pd.DataFrame(all_failing_records_export)
                            csv = export_df.to_csv(index=False)
                            st.download_button(
                                label="💾 Download Actual Failing Records",
                                data=csv,
                                file_name=f"actual_failing_records_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime="text/csv"
                            )
                        else:
                            st.warning("No failing records data to export")
                
                with col3:
                    if st.button("🗑️ Clear Selection", key="clear_selection"):
                        st.rerun()
                
                # Deep dive investigation when button is clicked
                if investigate_button:
                    st.markdown("---")
                    st.markdown("### 🔬 **Deep Dive Investigation Results**")
                    
                    if selected_df.empty:
                        st.warning("⚠️ No tests selected. Please select tests to investigate.")
                    else:
                        # Count failed vs passed tests
                        failed_count = len(selected_df[selected_df['status'] == 'fail']) if 'status' in selected_df.columns else 0
                        passed_count = len(selected_df[selected_df['status'] == 'pass']) if 'status' in selected_df.columns else 0
                        
                        st.success(f"🔍 Investigating {len(selected_df)} selected tests ({failed_count} failed, {passed_count} passed)...")
                        
                        # Show investigation summary
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("##### 📊 **Investigation Summary**")
                            summary_data = {
                                "Total Tests Selected": len(selected_df),
                                "Failed Tests": failed_count,
                                "Passed Tests": passed_count,
                                "Domains Affected": selected_df['domain'].nunique() if 'domain' in selected_df.columns else 0,
                                "Tables Affected": selected_df['table_name'].nunique() if 'table_name' in selected_df.columns else 0,
                                "Average Score": f"{selected_df['column_score'].mean():.1f}%" if 'column_score' in selected_df.columns else "N/A"
                            }
                            
                            for key, value in summary_data.items():
                                if isinstance(value, (int, float)) and not isinstance(value, str):
                                    st.write(f"**{key}**: {value:,}")
                                else:
                                    st.write(f"**{key}**: {value}")
                        
                        with col2:
                            st.markdown("##### ⚠️ **Test Status & Performance Breakdown**")
                            if 'status' in selected_df.columns:
                                # Show status breakdown
                                status_counts = selected_df['status'].value_counts()
                                for status, count in status_counts.items():
                                    status_color = "❌" if status == "fail" else "✅"
                                    st.write(f"{status_color} **{status.title()}**: {count} tests")
                            
                            # Show performance distribution
                            if 'column_score' in selected_df.columns:
                                st.markdown("---")
                                score_ranges = {
                                    'Excellent (90-100%)': len(selected_df[selected_df['column_score'] >= 90]),
                                    'Good (80-89%)': len(selected_df[(selected_df['column_score'] >= 80) & (selected_df['column_score'] < 90)]),
                                    'Fair (70-79%)': len(selected_df[(selected_df['column_score'] >= 70) & (selected_df['column_score'] < 80)]),
                                    'Poor (60-69%)': len(selected_df[(selected_df['column_score'] >= 60) & (selected_df['column_score'] < 70)]),
                                    'Critical (<60%)': len(selected_df[selected_df['column_score'] < 60])
                                }
                                
                                for range_name, count in score_ranges.items():
                                    if count > 0:
                                        if 'Critical' in range_name:
                                            st.write(f"🔴 **{range_name}**: {count} tests")
                                        elif 'Poor' in range_name:
                                            st.write(f"🟠 **{range_name}**: {count} tests")
                                        elif 'Fair' in range_name:
                                            st.write(f"🟡 **{range_name}**: {count} tests")
                                        elif 'Good' in range_name:
                                            st.write(f"🟢 **{range_name}**: {count} tests")
                                        else:
                                            st.write(f"✅ **{range_name}**: {count} tests")
                        
                        # Detailed Analysis by Test - WITH TOTAL FAILED RECORDS COUNT
                        st.markdown("##### 🔍 **Detailed Test Analysis**")

                        for idx, (_, test_row) in enumerate(selected_df.iterrows()):
                            domain = test_row.get('domain', 'Unknown')
                            table_name = test_row.get('table_name', 'Unknown')
                            column_name = test_row.get('column_name', 'Unknown')
                            column_score = test_row.get('column_score', 0)
                            status = test_row.get('status', 'unknown')
                            
                            # Get total failed records count for this test
                            try:
                                total_failed_query = """
                                SELECT COUNT(*) as total_failed_records
                                FROM failing_records 
                                WHERE domain = %s AND table_name = %s AND column_name = %s
                                """
                                
                                failed_count_result = db.run_query_with_params(total_failed_query, (domain, table_name, column_name))
                                total_failed_records = failed_count_result.iloc[0]['total_failed_records'] if not failed_count_result.empty else 0
                                
                            except Exception as e:
                                total_failed_records = 0
                            
                            # Determine status color and icon
                            if status == 'fail':
                                status_color = "#dc2626"
                                status_icon = "❌"
                                bg_color = "#fef2f2"
                            else:
                                status_color = "#059669" 
                                status_icon = "✅"
                                bg_color = "#f0fdf4"
                            
                            st.markdown(f"""
                            <div style="
                                background: {bg_color};
                                border: 1px solid {status_color}40;
                                border-radius: 8px;
                                padding: 1rem;
                                margin: 1rem 0;
                            ">
                                <h6 style="color: {status_color}; margin: 0 0 0.5rem 0;">
                                    {status_icon} Test {idx + 1}: {domain}.{table_name}.{column_name}
                                </h6>
                                <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 1rem;">
                                    <div>
                                        <strong>Overall Score:</strong><br>
                                        <span style="color: {status_color}; font-size: 1.2rem; font-weight: bold;">{column_score:.1f}%</span>
                                    </div>
                                    <div>
                                        <strong>Status:</strong><br>
                                        <span style="color: {status_color};">{status.title()}</span>
                                    </div>
                                    <div>
                                        <strong>Failed Records:</strong><br>
                                        <span style="color: {status_color}; font-weight: bold;">{total_failed_records:,}</span>
                                    </div>
                                    <div>
                                        <strong>Domain:</strong><br>
                                        {domain.upper()}
                                    </div>
                                    <div>
                                        <strong>Table:</strong><br>
                                        {table_name}
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Show dimension scores with descriptions for scores < 100%
                            dimension_scores = {}
                            dimension_issues = []
                            
                            for dim_col in ['completeness_score', 'uniqueness_score', 'consistency_score', 'validity_score', 'accuracy_score']:
                                if dim_col in test_row and pd.notna(test_row[dim_col]):
                                    dimension = dim_col.replace('_score', '')
                                    score = test_row[dim_col]
                                    dimension_scores[dimension] = score
                                    
                                    # Collect dimensions with issues (< 100%)
                                    if score < 100:
                                        dim_config = DQ_DIMENSIONS.get(dimension, {})
                                        dimension_issues.append({
                                            'name': dim_config.get('name', dimension.title()),
                                            'score': score,
                                            'description': dim_config.get('description', 'Data quality dimension'),
                                            'icon': dim_config.get('icon', '📊'),
                                            'color': dim_config.get('color', '#667eea')
                                        })
                            
                            if dimension_scores:
                                st.markdown("**Dimension Breakdown:**")
                                cols = st.columns(len(dimension_scores))
                                for i, (dim, score) in enumerate(dimension_scores.items()):
                                    with cols[i]:
                                        score_color = "#059669" if score >= 80 else "#f59e0b" if score >= 60 else "#dc2626"
                                        st.markdown(f"""
                                        <div style="text-align: center; padding: 0.5rem; background: {score_color}20; border-radius: 6px;">
                                            <div style="color: {score_color}; font-weight: bold; font-size: 1.1rem;">{score:.1f}%</div>
                                            <div style="font-size: 0.8rem; color: #6b7280;">{dim.title()}</div>
                                        </div>
                                        """, unsafe_allow_html=True)
                            
                            # Show dimension descriptions for any dimension < 100% - WITH FAILED RECORDS COUNT PER DIMENSION
                            if dimension_issues:
                                st.markdown("**🔍 Dimension Analysis (Issues Found):**")
                                
                                for issue in dimension_issues:
                                    # Load actual test descriptions and failed records count for this dimension
                                    try:
                                        dimension_name = issue['name'].lower()
                                        
                                        # Query to get actual test descriptions AND count of failed records for this dimension
                                        desc_query = """
                                        SELECT DISTINCT test_description, check_type
                                        FROM failing_records 
                                        WHERE domain = %s AND table_name = %s AND column_name = %s AND dimension = %s
                                        """
                                        
                                        # Query to count failed records for this specific dimension
                                        count_query = """
                                        SELECT COUNT(*) as dimension_failed_count
                                        FROM failing_records 
                                        WHERE domain = %s AND table_name = %s AND column_name = %s AND dimension = %s
                                        """
                                        
                                        descriptions = db.run_query_with_params(desc_query, (domain, table_name, column_name, dimension_name.title()))
                                        failed_count_result = db.run_query_with_params(count_query, (domain, table_name, column_name, dimension_name.title()))
                                        
                                        dimension_failed_count = failed_count_result.iloc[0]['dimension_failed_count'] if not failed_count_result.empty else 0
                                        
                                        # Build description text from actual failing records
                                        if not descriptions.empty:
                                            db_descriptions = []
                                            for _, desc_row in descriptions.iterrows():
                                                check_type = desc_row['check_type']
                                                test_desc = desc_row['test_description']
                                                db_descriptions.append(f"{test_desc}")
                                            
                                            actual_description = "<br>".join(db_descriptions)
                                        else:
                                            # Fallback to generic description if no failing records found
                                            actual_description = f"**Issue:** {issue['description']}"
                                            
                                    except Exception as e:
                                        # Fallback to generic description on error
                                        actual_description = f"**Issue:** {issue['description']}"
                                        dimension_failed_count = 0
                                    
                                    st.markdown(f"""
                                    <div style="
                                        background: linear-gradient(135deg, {issue['color']}10 0%, {issue['color']}05 100%);
                                        border-left: 4px solid {issue['color']};
                                        border-radius: 6px;
                                        padding: 1rem;
                                        margin: 0.5rem 0;
                                    ">
                                        <div style="display: flex; align-items: center; margin-bottom: 0.5rem;">
                                            <span style="font-size: 1.2rem; margin-right: 0.5rem;">{issue['icon']}</span>
                                            <strong style="color: {issue['color']}; font-size: 1.1rem;">{issue['name']}</strong>
                                            <span style="margin-left: auto; color: {issue['color']}; font-weight: bold;">{issue['score']:.1f}%</span>
                                        </div>
                                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                                            <div style="color: #64748b; font-size: 0.9rem;">
                                                <strong>Failed Records:</strong> <span style="color: {issue['color']}; font-weight: bold;">{dimension_failed_count:,}</span>
                                            </div>
                                        </div>
                                        <div style="color: #64748b; margin: 0; font-size: 0.9rem; line-height: 1.4;">
                                            {actual_description}
                                        </div>
                                    </div>
                                    """, unsafe_allow_html=True)
                            else:
                                st.success("✅ All dimensions performing at 100% - no issues detected!")
            
            else:
                st.info("💡 **Select tests from the table above** to begin your investigation. Use the checkboxes to select tests you want to analyze in detail.")

    st.markdown("---")

    # Advanced Analytics Section
    st.markdown("### 🎯 **Advanced Analytics & Insights**")

    # Show what's being analyzed
    if dimension_filter and dimension_filter != "All":
        st.info(f"📊 **Dimension Focus**: Advanced insights for {DQ_DIMENSIONS.get(dimension_filter, {}).get('name', dimension_filter.title())} dimension")
    else:
        st.info("📊 **Comprehensive Analysis**: Advanced insights across all dimensions")

    # Performance Trends by Time
    st.markdown("#### ⏰ **Performance Trends by Time**")

    if not kpi_results.empty:
        # Ensure execution_timestamp is datetime type
        kpi_results['execution_timestamp'] = pd.to_datetime(kpi_results['execution_timestamp'])
        
        # Create time-based grouping - group by date and hour to show full time range
        kpi_results['date_hour'] = kpi_results['execution_timestamp'].dt.floor('H')
        
        # Adapt based on dimension filter
        if dimension_filter and dimension_filter != "All":
            dimension_column = f"{dimension_filter.lower()}_score"
            filtered_data = kpi_results[kpi_results[dimension_column].notna()]
            
            if not filtered_data.empty:
                # Group by date_hour to show trends for specific dimension
                time_performance = filtered_data.groupby('date_hour').agg({
                    dimension_column: 'mean',
                    'column_score': 'mean'  # Keep overall score for comparison
                }).reset_index()
                
                # Also create hourly aggregation for patterns
                filtered_data['hour'] = filtered_data['execution_timestamp'].dt.hour
                hourly_performance = filtered_data.groupby('hour').agg({
                    dimension_column: 'mean'
                }).reset_index()
            else:
                time_performance = pd.DataFrame()
                hourly_performance = pd.DataFrame()
        else:
            # Group by date_hour to show trends across all dimensions
            time_performance = kpi_results.groupby('date_hour').agg({
                'column_score': 'mean'
            }).reset_index()
            
            # Also create hourly aggregation for comparison
            kpi_results['hour'] = kpi_results['execution_timestamp'].dt.hour
            hourly_performance = kpi_results.groupby('hour').agg({
                'column_score': 'mean'
            }).reset_index()
        
        # Create two charts: one for full time range, one for hourly patterns
        col1, col2 = st.columns(2)
        
        with col1:
            if dimension_filter and dimension_filter != "All":
                st.markdown(f"**📅 {dimension_filter.title()} Performance Over Time**")
                if not time_performance.empty:
                    dimension_column = f"{dimension_filter.lower()}_score"
                    time_chart_data = {
                        "data": [
                            {
                                "x": [d.strftime('%Y-%m-%d %H:%M') for d in time_performance['date_hour']],
                                "y": time_performance[dimension_column].tolist(),
                                "type": "scatter",
                                "mode": "lines+markers",
                                "name": f"{dimension_filter.title()} Score",
                                "line": {"color": DQ_DIMENSIONS.get(dimension_filter, {}).get('color', 'blue'), "width": 3},
                                "marker": {"size": 8},
                                "hovertemplate": f"<b>%{{x}}</b><br>{dimension_filter.title()} Score: %{{y:.1f}}%<extra></extra>"
                            }
                        ],
                        "layout": {
                            "title": f"{dimension_filter.title()} Performance Over Time",
                            "xaxis": {"title": "Date & Time"},
                            "yaxis": {"title": f"{dimension_filter.title()} Score (%)"},
                            "height": 400
                        }
                    }
                    create_interactive_chart(time_chart_data, height=400)
                else:
                    st.warning(f"No time performance data for {dimension_filter.title()}")
            else:
                st.markdown("**📅 Performance Over Time Range**")
                if not time_performance.empty:
                    time_chart_data = {
                        "data": [
                            {
                                "x": [d.strftime('%Y-%m-%d %H:%M') for d in time_performance['date_hour']],
                                "y": time_performance['column_score'].tolist(),
                                "type": "scatter",
                                "mode": "lines+markers",
                                "name": "DQ Score",
                                "line": {"color": "blue", "width": 3},
                                "marker": {"size": 8},
                                "hovertemplate": "<b>%{x}</b><br>DQ Score: %{y:.1f}%<extra></extra>"
                            }
                        ],
                        "layout": {
                            "title": "Performance Over Selected Time Range",
                            "xaxis": {"title": "Date & Time"},
                            "yaxis": {"title": "DQ Score (%)"},
                            "height": 400
                        }
                    }
                    create_interactive_chart(time_chart_data, height=400)
        
        with col2:
            st.markdown("**📈 Daily Performance Trends**")
            # Create daily aggregation for trend analysis
            kpi_results['date'] = kpi_results['execution_timestamp'].dt.date
            
            if dimension_filter and dimension_filter != "All":
                dimension_column = f"{dimension_filter.lower()}_score"
                filtered_data = kpi_results[kpi_results[dimension_column].notna()]
                
                if not filtered_data.empty:
                    daily_performance = filtered_data.groupby('date').agg({
                        dimension_column: 'mean',
                        'column_score': 'mean'  # Overall score for comparison
                    }).reset_index()
                    
                    daily_chart_data = {
                        "data": [
                            {
                                "x": [d.strftime('%Y-%m-%d') for d in daily_performance['date']],
                                "y": daily_performance[dimension_column].tolist(),
                                "type": "scatter",
                                "mode": "lines+markers",
                                "name": f"Daily {dimension_filter.title()} Score",
                                "line": {"color": DQ_DIMENSIONS.get(dimension_filter, {}).get('color', 'blue'), "width": 3},
                                "marker": {"size": 8},
                                "hovertemplate": f"<b>%{{x}}</b><br>{dimension_filter.title()} Score: %{{y:.1f}}%<extra></extra>"
                            }
                        ],
                        "layout": {
                            "title": f"Daily {dimension_filter.title()} Trends",
                            "xaxis": {"title": "Date"},
                            "yaxis": {"title": f"{dimension_filter.title()} Score (%)"},
                            "height": 400
                        }
                    }
                    create_interactive_chart(daily_chart_data, height=400)
                else:
                    st.warning(f"No daily data for {dimension_filter.title()}")
            else:
                daily_performance = kpi_results.groupby('date').agg({
                    'column_score': 'mean'
                }).reset_index()
                
                # Calculate pass rate (columns scoring >= 80%)
                daily_pass_rate = kpi_results.groupby('date').apply(
                    lambda x: (x['column_score'] >= 80).mean() * 100
                ).reset_index()
                daily_pass_rate.columns = ['date', 'pass_rate']
                
                # Merge the dataframes
                daily_performance = daily_performance.merge(daily_pass_rate, on='date')
                
                daily_chart_data = {
                    "data": [
                        {
                            "x": [d.strftime('%Y-%m-%d') for d in daily_performance['date']],
                            "y": daily_performance['column_score'].tolist(),
                            "type": "scatter",
                            "mode": "lines+markers",
                            "name": "Daily Avg DQ Score",
                            "line": {"color": "blue", "width": 3},
                            "marker": {"size": 8},
                            "yaxis": "y",
                            "hovertemplate": "<b>%{x}</b><br>Avg Score: %{y:.1f}%<extra></extra>"
                        },
                        {
                            "x": [d.strftime('%Y-%m-%d') for d in daily_performance['date']],
                            "y": daily_performance['pass_rate'].tolist(),
                            "type": "scatter",
                            "mode": "lines+markers",
                            "name": "Daily Pass Rate (%)",
                            "line": {"color": "green", "width": 3},
                            "marker": {"size": 8},
                            "yaxis": "y2",
                            "hovertemplate": "<b>%{x}</b><br>Pass Rate: %{y:.1f}%<extra></extra>"
                        }
                    ],
                    "layout": {
                        "title": "Daily Performance Trends",
                        "xaxis": {"title": "Date"},
                        "yaxis": {"title": "DQ Score (%)", "side": "left"},
                        "yaxis2": {"title": "Pass Rate (%)", "side": "right", "overlaying": "y"},
                        "height": 400
                    }
                }
                create_interactive_chart(daily_chart_data, height=400)

    # Quality Score Distribution Analysis
    st.markdown("#### ⚠️ **Quality Impact Analysis**")

    if not kpi_results.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            # Score distribution by domain
            st.markdown("**📦 Score Distribution by Domain**")
            if dimension_filter and dimension_filter != "All":
                dimension_column = f"{dimension_filter.lower()}_score"
                filtered_data = kpi_results[kpi_results[dimension_column].notna()]
                
                if not filtered_data.empty:
                    create_box_chart(
                        df=filtered_data,
                        y_col=dimension_column,
                        group_col="domain",
                        title=f"📦 {dimension_filter.title()} Score Distribution by Domain",
                        height=400
                    )
                else:
                    st.warning(f"No distribution data for {dimension_filter.title()}")
            else:
                create_box_chart(
                    df=kpi_results,
                    y_col="column_score",
                    group_col="domain",
                    title="📦 Score Distribution by Domain",
                    height=400
                )
        
        with col2:
            # Performance summary analysis
            if dimension_filter and dimension_filter != "All":
                st.markdown(f"**💼 {dimension_filter.title()} Impact by Table**")
                dimension_column = f"{dimension_filter.lower()}_score"
                filtered_data = kpi_results[kpi_results[dimension_column].notna()]
                
                if not filtered_data.empty:
                    # Get table performance for specific dimension
                    table_impact = filtered_data.groupby(['domain', 'table_name']).agg({
                        dimension_column: ['mean', 'count', 'std']
                    }).round(2)
                    
                    table_impact.columns = ['avg_score', 'test_count', 'score_std']
                    table_impact = table_impact.reset_index()
                    table_impact['table_full_name'] = table_impact['domain'] + '.' + table_impact['table_name']
                    
                    # Sort by average score
                    table_impact = table_impact.sort_values('avg_score', ascending=True)  # Show worst performers first
                    
                    # Show bottom 10 performers
                    bottom_tables = table_impact.head(10)
                    
                    impact_chart_data = {
                        "data": [{
                            "x": bottom_tables['avg_score'].tolist(),
                            "y": bottom_tables['table_full_name'].tolist(),
                            "type": "bar",
                            "orientation": "h",
                            "name": f"{dimension_filter.title()} Score",
                            "marker": {"color": DQ_DIMENSIONS.get(dimension_filter, {}).get('color', 'lightblue')},
                            "hovertemplate": f"<b>%{{y}}</b><br>{dimension_filter.title()} Score: %{{x:.1f}}%<br>Tests: %{{customdata}}<extra></extra>",
                            "customdata": bottom_tables['test_count'].tolist()
                        }],
                        "layout": {
                            "title": f"💼 Lowest {dimension_filter.title()} Performing Tables",
                            "xaxis": {"title": f"{dimension_filter.title()} Score (%)"},
                            "yaxis": {"title": "Table"},
                            "margin": {"l": 150},
                            "height": 400
                        }
                    }
                    
                    create_interactive_chart(impact_chart_data, height=400)
                else:
                    st.warning(f"No table impact data for {dimension_filter.title()}")
            else:
                st.markdown("**💼 Quality Score by Table Performance**")
                # Get table performance using table_score
                table_impact = kpi_results.groupby(['domain', 'table_name']).agg({
                    'column_score': ['mean', 'count'],
                    'table_score': 'first'  # Get table score
                }).round(2)
                
                table_impact.columns = ['avg_column_score', 'column_count', 'table_score']
                table_impact = table_impact.reset_index()
                table_impact['table_full_name'] = table_impact['domain'] + '.' + table_impact['table_name']
                
                # Sort by table score (show worst performers first)
                table_impact = table_impact.sort_values('table_score', ascending=True)
                
                # Show bottom 10 performers
                bottom_tables = table_impact.head(10)
                
                impact_chart_data = {
                    "data": [{
                        "x": bottom_tables['table_score'].tolist(),
                        "y": bottom_tables['table_full_name'].tolist(),
                        "type": "bar",
                        "orientation": "h",
                        "name": "Table Score",
                        "marker": {"color": "#ff6b6b"},
                        "hovertemplate": "<b>%{y}</b><br>Table Score: %{x:.1f}%<br>Columns: %{customdata}<extra></extra>",
                        "customdata": bottom_tables['column_count'].tolist()
                    }],
                    "layout": {
                        "title": "💼 Lowest Performing Tables (Need Attention)",
                        "xaxis": {"title": "Table Score (%)"},
                        "yaxis": {"title": "Table"},
                        "margin": {"l": 150},
                        "height": 400
                    }
                }
                
                create_interactive_chart(impact_chart_data, height=400)

    st.markdown("---")

    # Export functionality
    st.markdown("### 📤 **Export & Actions**")

    # Show what data will be exported based on current filters
    if dimension_filter and dimension_filter != "All":
        export_description = f"Filtered data for {DQ_DIMENSIONS.get(dimension_filter, {}).get('name', dimension_filter.title())} dimension"
    else:
        export_description = "Complete dataset with all dimensions"

    if selected_domains:
        domain_description = f" from {', '.join(selected_domains)} domain(s)"
    else:
        domain_description = " from all domains"

    st.info(f"💡 **Export Scope**: {export_description}{domain_description}")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("📥 Export All Data", use_container_width=True, key="export_all"):
            # Create comprehensive export with metadata
            export_data = kpi_results.copy()
            
            # Add export metadata
            export_data['export_timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            export_data['export_filters'] = f"Dimension: {dimension_filter}, Domains: {selected_domains}"
            
            csv = export_data.to_csv(index=False)
            st.download_button(
                label="💾 Download Full Dataset",
                data=csv,
                file_name=f"dq_analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
            
            # Log the export action
            log_user_action('data_export', {
                'export_type': 'full_dataset',
                'record_count': len(export_data),
                'filters': {
                    'dimension': dimension_filter,
                    'domains': selected_domains
                }
            }, current_user)

    with col2:
        if st.button("📊 Generate Report", use_container_width=True, key="generate_report"):
            # Create comprehensive report
            report_content = f"""# Data Quality Analytics Report
    Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    User: {current_user}

    ## Executive Summary
    - Analysis Period: {start_date.strftime('%Y-%m-%d') if hasattr(start_date, 'strftime') else start_date} to {end_date.strftime('%Y-%m-%d') if hasattr(end_date, 'strftime') else end_date}
    - Dimension Focus: {dimension_filter if dimension_filter != "All" else "All Dimensions"}
    - Domains Analyzed: {', '.join(selected_domains) if selected_domains else 'All Domains'}
    - Total Columns Analyzed: {len(kpi_results):,}

    ## Key Metrics
    """
            
            # Add key metrics
            if not kpi_results.empty:
                if dimension_filter and dimension_filter != "All":
                    dimension_column = f"{dimension_filter.lower()}_score"
                    filtered_data = kpi_results[kpi_results[dimension_column].notna()]
                    if not filtered_data.empty:
                        avg_score = filtered_data[dimension_column].mean()
                        pass_rate = (filtered_data[dimension_column] >= 80).mean()
                        total_columns = len(filtered_data)
                        report_content += f"""
    - Average {dimension_filter.title()} Score: {avg_score:.1f}%
    - {dimension_filter.title()} Pass Rate: {pass_rate:.1%}
    - Columns Tested for {dimension_filter.title()}: {total_columns:,}
    """
                else:
                    avg_score = kpi_results['column_score'].mean()
                    pass_rate = (kpi_results['column_score'] >= 80).mean()
                    total_columns = len(kpi_results)
                    report_content += f"""
    - Overall Average Score: {avg_score:.1f}%
    - Overall Pass Rate: {pass_rate:.1%}
    - Total Columns Analyzed: {total_columns:,}
    """
            
            report_content += f"""

    ## Domain Performance Summary
    """
            
            # Add domain performance
            if not kpi_results.empty:
                if dimension_filter and dimension_filter != "All":
                    dimension_column = f"{dimension_filter.lower()}_score"
                    filtered_data = kpi_results[kpi_results[dimension_column].notna()]
                    if not filtered_data.empty:
                        domain_perf = filtered_data.groupby('domain')[dimension_column].agg(['mean', 'count']).round(2)
                        for domain, stats in domain_perf.iterrows():
                            report_content += f"- {domain.upper()}: Avg {dimension_filter.title()} Score = {stats['mean']:.1f}%, Columns = {stats['count']}\n"
                else:
                    domain_perf = kpi_results.groupby('domain')['column_score'].agg(['mean', 'count']).round(2)
                    for domain, stats in domain_perf.iterrows():
                        report_content += f"- {domain.upper()}: Avg Score = {stats['mean']:.1f}%, Columns = {stats['count']}\n"
            
            report_content += f"""

    ## Recommendations
    1. Focus on domains with scores below 80%
    2. Investigate columns with consistently low scores
    3. Review data quality processes for failing dimensions
    4. Implement monitoring for critical quality metrics
    5. Schedule regular quality assessments

    ## Technical Details
    - Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    - Data Source: DBT KPI Tables (column_kpi, table_kpi, global_kpi)
    - Analysis Framework: Dimensional Data Quality Assessment
    """
            
            st.download_button(
                label="📋 Download Analytics Report",
                data=report_content,
                file_name=f"dq_analytics_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )
            
            st.success("📋 Report generated successfully!")
            
            # Log the report generation
            log_user_action('report_generated', {
                'report_type': 'analytics_report',
                'filters': {
                    'dimension': dimension_filter,
                    'domains': selected_domains
                }
            }, current_user)

    with col3:
        if st.button("🔄 Refresh Data", use_container_width=True, key="refresh_data"):
            # Clear any cached data and reload
            st.cache_data.clear()
            st.success("🔄 Data refreshed! Reloading page...")
            st.rerun()

    with col4:
        if st.button("📈 Quick Insights", use_container_width=True, key="quick_insights"):
            # Generate quick insights popup
            insights = []
            
            if not kpi_results.empty:
                if dimension_filter and dimension_filter != "All":
                    dimension_column = f"{dimension_filter.lower()}_score"
                    filtered_data = kpi_results[kpi_results[dimension_column].notna()]
                    
                    if not filtered_data.empty:
                        avg_score = filtered_data[dimension_column].mean()
                        worst_domain = filtered_data.groupby('domain')[dimension_column].mean().idxmin()
                        best_domain = filtered_data.groupby('domain')[dimension_column].mean().idxmax()
                        
                        insights.append(f"🎯 **{dimension_filter.title()} Focus**: Average score is {avg_score:.1f}%")
                        insights.append(f"📈 **Best Performing**: {best_domain.upper()} domain")
                        insights.append(f"📉 **Needs Attention**: {worst_domain.upper()} domain")
                        
                        if avg_score < 80:
                            insights.append(f"⚠️ **Action Required**: {dimension_filter.title()} score below 80% threshold")
                        else:
                            insights.append(f"✅ **Good Performance**: {dimension_filter.title()} score above 80% threshold")
                else:
                    avg_score = kpi_results['column_score'].mean()
                    pass_rate = (kpi_results['column_score'] >= 80).mean()
                    total_columns = len(kpi_results)
                    failing_columns = len(kpi_results[kpi_results['column_score'] < 80])
                    
                    insights.append(f"📊 **Overall Health**: {avg_score:.1f}% average score")
                    insights.append(f"✅ **Pass Rate**: {pass_rate:.1%} of columns passing")
                    insights.append(f"📋 **Total Columns**: {total_columns:,} analyzed")
                    
                    if failing_columns > 0:
                        insights.append(f"🚨 **Action Items**: {failing_columns:,} columns need attention")
                    else:
                        insights.append("🎉 **All Good**: No columns failing quality checks")
            
            # Display insights in an info box
            insights_text = "\n".join([f"• {insight}" for insight in insights])
            st.info(f"💡 **Quick Data Quality Insights**:\n\n{insights_text}")

    # Additional Export Options
    st.markdown("---")
    # st.markdown("#### 📋 **Specialized Exports**")

    # col1, col2, col3 = st.columns(3)

    # with col1:
    #     if st.button("🚨 Export Failed Tests Only", use_container_width=True, key="export_failed"):
    #         if not kpi_results.empty:
    #             if dimension_filter and dimension_filter != "All":
    #                 dimension_column = f"{dimension_filter.lower()}_score"
    #                 failed_data = kpi_results[kpi_results[dimension_column] < 80]
    #             else:
    #                 failed_data = kpi_results[kpi_results['column_score'] < 80]
                
    #             if not failed_data.empty:
    #                 failed_csv = failed_data.to_csv(index=False)
    #                 st.download_button(
    #                     label="💾 Download Failed Tests",
    #                     data=failed_csv,
    #                     file_name=f"failed_tests_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
    #                     mime="text/csv"
    #                 )
    #                 st.success(f"📤 Exported {len(failed_data)} failed tests")
    #             else:
    #                 st.info("✅ No failed tests to export!")

    # with col2:
    #     if st.button("📈 Export Summary Stats", use_container_width=True, key="export_summary"):
    #         if not kpi_results.empty:
    #             # Create summary statistics
    #             if dimension_filter and dimension_filter != "All":
    #                 dimension_column = f"{dimension_filter.lower()}_score"
    #                 filtered_data = kpi_results[kpi_results[dimension_column].notna()]
    #                 summary_stats = filtered_data.groupby('domain').agg({
    #                     dimension_column: ['mean', 'std', 'min', 'max', 'count'],
    #                     'table_name': 'nunique'
    #                 }).round(2)
    #                 summary_stats.columns = [f"{dimension_filter}_avg", f"{dimension_filter}_std", f"{dimension_filter}_min", f"{dimension_filter}_max", f"{dimension_filter}_count", "unique_tables"]
    #             else:
    #                 summary_stats = kpi_results.groupby('domain').agg({
    #                     'column_score': ['mean', 'std', 'min', 'max', 'count'],
    #                     'table_name': 'nunique'
    #                 }).round(2)
    #                 summary_stats.columns = ['avg_score', 'std_score', 'min_score', 'max_score', 'column_count', 'unique_tables']
                
    #             summary_csv = summary_stats.to_csv()
    #             st.download_button(
    #                 label="💾 Download Summary Stats",
    #                 data=summary_csv,
    #                 file_name=f"summary_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
    #                 mime="text/csv"
    #             )

    # with col3:
    #     if st.button("🎯 Export Action Items", use_container_width=True, key="export_actions"):
    #         if not kpi_results.empty:
    #             # Create action items for failing tests
    #             if dimension_filter and dimension_filter != "All":
    #                 dimension_column = f"{dimension_filter.lower()}_score"
    #                 action_items = kpi_results[kpi_results[dimension_column] < 80].copy()
    #                 action_items['priority'] = action_items[dimension_column].apply(
    #                     lambda x: 'HIGH' if x < 60 else 'MEDIUM' if x < 80 else 'LOW'
    #                 )
    #                 action_items['action_needed'] = f"Fix {dimension_filter.lower()} issues"
    #             else:
    #                 action_items = kpi_results[kpi_results['column_score'] < 80].copy()
    #                 action_items['priority'] = action_items['column_score'].apply(
    #                     lambda x: 'HIGH' if x < 60 else 'MEDIUM' if x < 80 else 'LOW'
    #                 )
    #                 action_items['action_needed'] = "Fix data quality issues"
                
    #             action_items['assigned_to'] = action_items['domain'].apply(lambda x: f"{x.upper()} Team")
    #             action_items['due_date'] = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
                
    #             if not action_items.empty:
    #                 action_csv = action_items[['domain', 'table_name', 'column_name', 'column_score', 'priority', 'action_needed', 'assigned_to', 'due_date']].to_csv(index=False)
    #                 st.download_button(
    #                     label="💾 Download Action Items",
    #                     data=action_csv,
    #                     file_name=f"action_items_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
    #                     mime="text/csv"
    #                 )
    #                 st.success(f"📋 Generated {len(action_items)} action items")
    #             else:
    #                 st.info("🎉 No action items needed - all tests passing!")

    # # Footer
    # st.markdown("---")
    # st.caption("🎯 Analytics Dashboard • Real-time Data Quality Insights • Export & Action Management")