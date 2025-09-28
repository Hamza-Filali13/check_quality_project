"""
Utility functions for the Data Quality Dashboard
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from typing import Dict, List, Tuple, Optional
import numpy as np
from datetime import datetime, timedelta

def get_score_color(score: float) -> str:
    """Get color based on DQ score"""
    if score >= 90:
        return "#28a745"  # Green
    elif score >= 80:
        return "#ffc107"  # Yellow
    elif score >= 70:
        return "#fd7e14"  # Orange
    else:
        return "#dc3545"  # Red

def get_severity_level(score: float) -> str:
    """Get severity level based on score"""
    if score >= 90:
        return "Low"
    elif score >= 80:
        return "Medium"
    elif score >= 70:
        return "High"
    else:
        return "Critical"

def format_metric_card(title: str, value: str, delta: Optional[str] = None, 
                      color: str = "#1f4e79") -> str:
    """Generate HTML for a metric card"""
    delta_html = f'<div class="metric-delta">{delta}</div>' if delta else ''
    
    return f"""
    <div class="metric-card" style="border-left-color: {color};">
        <div class="metric-title">{title}</div>
        <div class="metric-value">{value}</div>
        {delta_html}
    </div>
    """

def create_gauge_chart(value: float, title: str, max_value: float = 100) -> go.Figure:
    """Create a gauge chart for KPI display"""
    fig = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = value,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': title},
        delta = {'reference': 80},
        gauge = {
            'axis': {'range': [None, max_value]},
            'bar': {'color': get_score_color(value)},
            'steps': [
                {'range': [0, 70], 'color': "lightgray"},
                {'range': [70, 90], 'color': "gray"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))
    
    fig.update_layout(height=300, margin=dict(l=20, r=20, t=40, b=20))
    return fig

def create_trend_chart(df: pd.DataFrame, x_col: str, y_col: str, 
                      color_col: Optional[str] = None, title: str = "") -> go.Figure:
    """Create a trend line chart"""
    if color_col:
        fig = px.line(df, x=x_col, y=y_col, color=color_col, 
                     title=title, markers=True)
    else:
        fig = px.line(df, x=x_col, y=y_col, title=title, markers=True)
    
    fig.update_layout(
        height=400,
        xaxis_title=x_col.replace('_', ' ').title(),
        yaxis_title=y_col.replace('_', ' ').title()
    )
    
    return fig

def create_heatmap(df: pd.DataFrame, x_col: str, y_col: str, 
                  value_col: str, title: str = "") -> go.Figure:
    """Create a heatmap visualization"""
    pivot_df = df.pivot_table(index=y_col, columns=x_col, values=value_col, fill_value=0)
    
    fig = px.imshow(
        pivot_df.values,
        x=pivot_df.columns,
        y=pivot_df.index,
        title=title,
        aspect='auto',
        color_continuous_scale='RdYlGn'
    )
    
    fig.update_layout(height=500)
    return fig

def create_distribution_chart(df: pd.DataFrame, column: str, 
                            title: str = "", bins: int = 20) -> go.Figure:
    """Create a distribution histogram"""
    fig = px.histogram(df, x=column, nbins=bins, title=title)
    fig.update_layout(
        height=400,
        xaxis_title=column.replace('_', ' ').title(),
        yaxis_title="Count"
    )
    return fig

def create_correlation_matrix(df: pd.DataFrame, columns: List[str], 
                            title: str = "Correlation Matrix") -> go.Figure:
    """Create a correlation matrix heatmap"""
    corr_matrix = df[columns].corr()
    
    fig = px.imshow(
        corr_matrix.values,
        x=corr_matrix.columns,
        y=corr_matrix.index,
        title=title,
        color_continuous_scale='RdBu',
        aspect='auto'
    )
    
    # Add correlation values as text
    for i in range(len(corr_matrix.columns)):
        for j in range(len(corr_matrix.index)):
            fig.add_annotation(
                x=i, y=j,
                text=str(round(corr_matrix.iloc[j, i], 2)),
                showarrow=False,
                font=dict(color="white" if abs(corr_matrix.iloc[j, i]) > 0.5 else "black")
            )
    
    fig.update_layout(height=500)
    return fig

def create_sunburst_chart(df: pd.DataFrame, path_columns: List[str], 
                         value_column: str, title: str = "") -> go.Figure:
    """Create a sunburst chart for hierarchical data"""
    fig = px.sunburst(
        df, 
        path=path_columns, 
        values=value_column,
        title=title
    )
    
    fig.update_layout(height=500)
    return fig

def calculate_data_quality_score(completeness: float, uniqueness: float, 
                               validity: float = 100.0, 
                               weights: Dict[str, float] = None) -> float:
    """Calculate overall data quality score"""
    if weights is None:
        weights = {"completeness": 0.4, "uniqueness": 0.3, "validity": 0.3}
    
    score = (
        completeness * weights.get("completeness", 0.4) +
        uniqueness * weights.get("uniqueness", 0.3) +
        validity * weights.get("validity", 0.3)
    )
    
    return round(score, 2)

def generate_data_profile(df: pd.DataFrame) -> Dict:
    """Generate a comprehensive data profile"""
    profile = {
        "shape": df.shape,
        "columns": list(df.columns),
        "dtypes": df.dtypes.to_dict(),
        "missing_values": df.isnull().sum().to_dict(),
        "missing_percentage": (df.isnull().sum() / len(df) * 100).round(2).to_dict(),
        "unique_values": df.nunique().to_dict(),
        "duplicate_rows": df.duplicated().sum(),
        "memory_usage": df.memory_usage(deep=True).sum(),
    }
    
    # Add numeric statistics
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) > 0:
        profile["numeric_stats"] = df[numeric_cols].describe().to_dict()
    
    # Add categorical statistics
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns
    if len(categorical_cols) > 0:
        profile["categorical_stats"] = {}
        for col in categorical_cols:
            profile["categorical_stats"][col] = {
                "unique_count": df[col].nunique(),
                "top_values": df[col].value_counts().head(5).to_dict()
            }
    
    return profile

def format_number(num: float, format_type: str = "auto") -> str:
    """Format numbers for display"""
    if pd.isna(num):
        return "N/A"
    
    if format_type == "percentage":
        return f"{num:.1f}%"
    elif format_type == "currency":
        return f"${num:,.2f}"
    elif format_type == "integer":
        return f"{int(num):,}"
    elif format_type == "decimal":
        return f"{num:.2f}"
    else:  # auto
        if num >= 1000000:
            return f"{num/1000000:.1f}M"
        elif num >= 1000:
            return f"{num/1000:.1f}K"
        else:
            return f"{num:.1f}"

def create_alert_message(severity: str, message: str, 
                        details: Optional[str] = None) -> None:
    """Create styled alert messages"""
    if severity == "success":
        st.success(f"✅ {message}")
    elif severity == "warning":
        st.warning(f"⚠️ {message}")
    elif severity == "error":
        st.error(f"❌ {message}")
    elif severity == "info":
        st.info(f"ℹ️ {message}")
    
    if details:
        with st.expander("Details"):
            st.write(details)

def export_data(df: pd.DataFrame, filename: str, format_type: str = "csv") -> bytes:
    """Export dataframe to various formats"""
    if format_type == "csv":
        return df.to_csv(index=False).encode("utf-8")
    elif format_type == "excel":
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="data")
        return output.getvalue()
    elif format_type == "json":
        return df.to_json(orient="records", date_format="iso").encode("utf-8")
    else:
        raise ValueError(f"Unsupported format: {format_type}")

def validate_data_quality_rules(df: pd.DataFrame, rules: Dict) -> Dict:
    """Validate data against quality rules"""
    results = {}
    
    for rule_name, rule_config in rules.items():
        rule_type = rule_config.get("type")
        column = rule_config.get("column")
        threshold = rule_config.get("threshold", 0)
        
        if rule_type == "completeness":
            completeness = (1 - df[column].isnull().sum() / len(df)) * 100
            results[rule_name] = {
                "value": completeness,
                "passed": completeness >= threshold,
                "threshold": threshold
            }
        
        elif rule_type == "uniqueness":
            uniqueness = (df[column].nunique() / len(df)) * 100
            results[rule_name] = {
                "value": uniqueness,
                "passed": uniqueness >= threshold,
                "threshold": threshold
            }
        
        elif rule_type == "range":
            min_val = rule_config.get("min")
            max_val = rule_config.get("max")
            in_range = df[column].between(min_val, max_val).sum()
            percentage = (in_range / len(df)) * 100
            results[rule_name] = {
                "value": percentage,
                "passed": percentage >= threshold,
                "threshold": threshold
            }
    
    return results

def create_executive_summary(results_df: pd.DataFrame, scores_df: pd.DataFrame) -> Dict:
    """Create executive summary of data quality"""
    summary = {}
    
    if not results_df.empty:
        summary["total_tests"] = len(results_df)
        summary["passed_tests"] = len(results_df[results_df["status"] == "pass"])
        summary["failed_tests"] = len(results_df[results_df["status"] == "fail"])
        summary["pass_rate"] = (summary["passed_tests"] / summary["total_tests"]) * 100
        
        # Domain breakdown
        summary["domains"] = {}
        for domain in results_df["domain"].unique():
            domain_data = results_df[results_df["domain"] == domain]
            summary["domains"][domain] = {
                "total_tests": len(domain_data),
                "passed_tests": len(domain_data[domain_data["status"] == "pass"]),
                "pass_rate": (len(domain_data[domain_data["status"] == "pass"]) / len(domain_data)) * 100
            }
    
    if not scores_df.empty:
        summary["avg_score"] = scores_df["dq_score"].mean()
        summary["min_score"] = scores_df["dq_score"].min()
        summary["max_score"] = scores_df["dq_score"].max()
        summary["total_tables"] = scores_df["table_name"].nunique()
    
    return summary

def get_recommendations(summary: Dict) -> List[str]:
    """Generate recommendations based on data quality summary"""
    recommendations = []
    
    if summary.get("pass_rate", 100) < 80:
        recommendations.append("🔴 Critical: Overall pass rate is below 80%. Immediate attention required.")
    
    if summary.get("avg_score", 100) < 70:
        recommendations.append("🟡 Warning: Average DQ score is below 70%. Consider reviewing data pipelines.")
    
    if summary.get("failed_tests", 0) > 10:
        recommendations.append("📊 High number of failed tests detected. Prioritize fixing critical issues.")
    
    # Domain-specific recommendations
    for domain, stats in summary.get("domains", {}).items():
        if stats.get("pass_rate", 100) < 70:
            recommendations.append(f"🏢 {domain.title()} domain needs attention - pass rate: {stats['pass_rate']:.1f}%")
    
    if not recommendations:
        recommendations.append("✅ Data quality looks good! Continue monitoring for any changes.")
    
    return recommendations