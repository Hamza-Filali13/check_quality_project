"""
Interactive Charts Helper
Creates truly interactive Plotly charts using HTML components to bypass Streamlit's SVG rendering
"""

import streamlit as st
import streamlit.components.v1 as components
import json
import uuid
from datetime import datetime


def create_interactive_chart(data, chart_type="scatter", config=None, height=400):
    """
    Create an interactive chart using HTML components with WebGL rendering
    
    Args:
        data: Dictionary containing chart data and layout
        chart_type: Type of chart ('scatter', 'bar', 'line', 'box', 'heatmap')
        config: Plotly config options
        height: Chart height in pixels
    
    Returns:
        None (renders the chart directly)
    """
    
    # Generate unique ID for this chart
    chart_id = f"plotly-chart-{uuid.uuid4().hex[:8]}"
    
    # Default config for interactive charts
    default_config = {
        "scrollZoom": True,
        "displaylogo": False,
        "displayModeBar": True,
        "staticPlot": False,
        "responsive": True,
        "modeBarButtonsToAdd": ["select2d", "lasso2d"],
        "toImageButtonOptions": {
            "format": "png",
            "filename": "chart",
            "height": 500,
            "width": 700,
            "scale": 1
        }
    }
    
    # Merge with user config
    if config:
        default_config.update(config)
    
    # Convert data to JSON strings for JavaScript with datetime handling
    def json_serializer(obj):
        """JSON serializer for datetime objects"""
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        elif hasattr(obj, 'strftime'):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    data_json = json.dumps(data.get('data', []), default=json_serializer)
    layout_json = json.dumps(data.get('layout', {}), default=json_serializer)
    config_json = json.dumps(default_config, default=json_serializer)
    
    # Create HTML with embedded Plotly
    html_content = f"""
    <div id="{chart_id}" style="width:100%;height:{height}px;"></div>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <script>
        (function() {{
            var data = {data_json};
            var layout = {layout_json};
            var config = {config_json};
            
            // Ensure responsive layout
            layout.autosize = true;
            layout.margin = layout.margin || {{}};
            
            // Force WebGL for scatter plots
            data.forEach(function(trace) {{
                if (trace.type === 'scatter' || (trace.mode && trace.mode.includes('markers'))) {{
                    trace.type = 'scattergl';  // Force WebGL rendering
                }}
            }});
            
            Plotly.newPlot('{chart_id}', data, layout, config);
            
            // Handle window resize
            window.addEventListener('resize', function() {{
                Plotly.Plots.resize('{chart_id}');
            }});
        }})();
    </script>
    """
    
    # Render the HTML component
    components.html(html_content, height=height + 50)


def create_scatter_chart(df, x_col, y_col, color_col=None, size_col=None, 
                        hover_data=None, title="Interactive Scatter Chart", height=400):
    """
    Create an interactive scatter chart with WebGL rendering
    """
    
    # Prepare data for the chart
    traces = []
    
    if color_col and color_col in df.columns:
        # Group by color column
        for category in df[color_col].unique():
            category_data = df[df[color_col] == category]
            
            # Convert datetime columns to strings for JSON serialization
            x_data = category_data[x_col].tolist()
            if hasattr(category_data[x_col].iloc[0], 'isoformat'):
                x_data = [x.isoformat() if hasattr(x, 'isoformat') else str(x) for x in x_data]
            
            trace = {
                "x": x_data,
                "y": category_data[y_col].tolist(),
                "mode": "markers",
                "type": "scattergl",  # Force WebGL
                "name": str(category),
                "marker": {
                    "size": category_data[size_col].tolist() if size_col and size_col in df.columns else 8,
                    "opacity": 0.8
                }
            }
            
            # Add hover data
            if hover_data:
                hover_text = []
                for _, row in category_data.iterrows():
                    hover_info = f"<b>{category}</b><br>"
                    hover_info += f"{x_col}: {row[x_col]}<br>"
                    hover_info += f"{y_col}: {row[y_col]}<br>"
                    for col in hover_data:
                        if col in row:
                            hover_info += f"{col}: {row[col]}<br>"
                    hover_text.append(hover_info)
                
                trace["hovertemplate"] = hover_text
            
            traces.append(trace)
    else:
        # Single trace
        # Convert datetime columns to strings for JSON serialization
        x_data = df[x_col].tolist()
        if hasattr(df[x_col].iloc[0], 'isoformat'):
            x_data = [x.isoformat() if hasattr(x, 'isoformat') else str(x) for x in x_data]
        
        trace = {
            "x": x_data,
            "y": df[y_col].tolist(),
            "mode": "markers",
            "type": "scattergl",  # Force WebGL
            "marker": {
                "size": df[size_col].tolist() if size_col and size_col in df.columns else 8,
                "opacity": 0.8
            }
        }
        traces.append(trace)
    
    # Create layout
    layout = {
        "title": title,
        "xaxis": {"title": x_col.replace('_', ' ').title()},
        "yaxis": {"title": y_col.replace('_', ' ').title()},
        "hovermode": "closest",
        "dragmode": "zoom"
    }
    
    # Create the chart
    chart_data = {
        "data": traces,
        "layout": layout
    }
    
    create_interactive_chart(chart_data, "scatter", height=height)


def create_bar_chart(df, x_col, y_col, color_col=None, title="Interactive Bar Chart", height=400):
    """
    Create an interactive bar chart
    """
    
    traces = []
    
    if color_col and color_col in df.columns:
        # Group by color column
        for category in df[color_col].unique():
            category_data = df[df[color_col] == category]
            
            trace = {
                "x": category_data[x_col].tolist(),
                "y": category_data[y_col].tolist(),
                "type": "bar",
                "name": str(category),
                "hovertemplate": f"<b>{category}</b><br>{x_col}: %{{x}}<br>{y_col}: %{{y}}<extra></extra>"
            }
            traces.append(trace)
    else:
        # Single trace
        trace = {
            "x": df[x_col].tolist(),
            "y": df[y_col].tolist(),
            "type": "bar",
            "hovertemplate": f"{x_col}: %{{x}}<br>{y_col}: %{{y}}<extra></extra>"
        }
        traces.append(trace)
    
    # Create layout
    layout = {
        "title": title,
        "xaxis": {"title": x_col.replace('_', ' ').title()},
        "yaxis": {"title": y_col.replace('_', ' ').title()},
        "dragmode": "zoom"
    }
    
    # Create the chart
    chart_data = {
        "data": traces,
        "layout": layout
    }
    
    create_interactive_chart(chart_data, "bar", height=height)


def create_box_chart(df, y_col, group_col=None, title="Interactive Box Plot", height=400):
    """
    Create an interactive box plot
    """
    
    traces = []
    
    if group_col and group_col in df.columns:
        # Group by group column
        for category in df[group_col].unique():
            category_data = df[df[group_col] == category]
            
            trace = {
                "y": category_data[y_col].tolist(),
                "type": "box",
                "name": str(category),
                "boxpoints": "outliers"
            }
            traces.append(trace)
    else:
        # Single trace
        trace = {
            "y": df[y_col].tolist(),
            "type": "box",
            "boxpoints": "outliers"
        }
        traces.append(trace)
    
    # Create layout
    layout = {
        "title": title,
        "yaxis": {"title": y_col.replace('_', ' ').title()},
        "dragmode": "zoom"
    }
    
    # Create the chart
    chart_data = {
        "data": traces,
        "layout": layout
    }
    
    create_interactive_chart(chart_data, "box", height=height)
