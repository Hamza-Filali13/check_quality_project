import streamlit as st
from streamlit_navigation_bar import st_navbar
from session_manager import session_manager
# Import page functions
from pages.home import run as home_run
from pages.analytics import run as analytics_run
from pages.login import run as login_run
from pages.dq_tests import run as dq_tests_run

# ---- App Config ----
try:
    st.set_page_config(
        page_title="DXC Data Quality Platform",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
except Exception:
    pass  # Ignore errors from set_page_config

# ---- Global Styling ----
st.markdown("""
<style>
    /* Hide sidebar completely */
    .css-1d391kg, .css-1rs6os, .css-17eq0hr, section[data-testid="stSidebar"] {
        display: none !important;
    }
    
    /* Main app container */
    .main .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        max-width: none !important;
        margin-top: 0 !important;
    }
    
    /* App container */
    .stApp {
        overflow-x: hidden;
        padding-top: 4rem !important; /* Space for navbar */
    }
    
    /* Navigation bar styling */
    .nav-container {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        z-index: 999;
        background: linear-gradient(135deg, #1f2937, #374151);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        border-bottom: 2px solid #3b82f6;
    }
    
    /* Modern scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(45deg, #667eea, #764ba2);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(45deg, #764ba2, #667eea);
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(45deg, #667eea, #764ba2);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        transition: all 0.3s ease;
        cursor: pointer;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
    }
    
    /* Ensure all elements are interactive */
    * {
        pointer-events: auto !important;
    }
    
    /* Hide default Streamlit header */
    header[data-testid="stHeader"] {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

# ---- Session Management ----
# Try to restore session from cookie
session_manager.restore_session()

# ---- Navigation Setup ----
def get_navigation_pages():
    """Get navigation pages based on authentication status (using original session variable)"""
    if st.session_state.get("allow_access", 0) == 1:
        return ["Home", "Analytics", "DQ Tests", "Logout"]
    else:
        return ["Login"]

def get_navbar_styles():
    """Get navigation bar styles"""
    return {
        "nav": {
            "background": "linear-gradient(135deg, #1f2937, #374151)",
            "justify-content": "center",
            "padding": "0.75rem 0",
            "box-shadow": "0 4px 12px rgba(0, 0, 0, 0.15)",
            "border-bottom": "2px solid #3b82f6",
        },
        "span": {
            "color": "#f9fafb",
            "padding": "12px 24px",
            "font-size": "16px",
            "font-weight": "500",
            "transition": "all 0.3s ease",
            "border-radius": "8px",
            "margin": "0 8px",
        },
        "active": {
            "background": "linear-gradient(135deg, #3b82f6, #1d4ed8)",
            "color": "white",
            "font-weight": "600",
            "padding": "12px 24px",
            "border-radius": "8px",
            "box-shadow": "0 4px 12px rgba(59, 130, 246, 0.4)",
        }
    }

# ---- Handle Logout ----
def handle_logout():
    """Handle logout action"""
    session_manager.logout()
    st.success("✅ Successfully logged out!")
    st.balloons()  # Fun logout animation
    # Don't call st.rerun() here - let the app naturally refresh

# ---- Render Navigation ----
pages = get_navigation_pages()
styles = get_navbar_styles()

# Add navbar container div
st.markdown('<div class="nav-container">', unsafe_allow_html=True)
selected = st_navbar(
    pages,
    styles=styles,
    options={"show_menu": False, "show_sidebar": False}
)
st.markdown('</div>', unsafe_allow_html=True)

# ---- Page Routing ----
def route_pages():
    """Route to appropriate page based on selection and authentication"""
    
    # Handle logout
    if selected == "Logout":
        handle_logout()
        return
    
    # Check authentication for protected pages (using original session variable)
    if selected in ["Home", "Analytics", "DQ Tests"]:
        if st.session_state.get("allow_access", 0) != 1:
            st.error("🔒 Please log in to access this page")
            login_run()
            return
    
    # Route to pages (using original session variable)
    is_authenticated = st.session_state.get("allow_access", 0) == 1
    
    if selected == "Home" or (is_authenticated and selected is None):
        home_run()
    elif selected == "Analytics":
        analytics_run()
    elif selected == "DQ Tests":
        dq_tests_run()
    elif selected == "Login" or not is_authenticated:
        login_run()
    else:
        # Default fallback
        if is_authenticated:
            home_run()
        else:
            login_run()

# Execute routing
route_pages()

# ---- Footer ----
if st.session_state.get("allow_access", 0) == 1:
    st.markdown("---")
    current_user = st.session_state.get("current_user", "Unknown")
    is_admin = st.session_state.get("is_admin", False)
    domains = st.session_state.get("domains", [])
    
    st.markdown(
        """
        <div style="text-align: center; color: #666; padding: 1rem; margin-top: 2rem;">
            <p>🏢 DXC Data Quality Platform © 2025 | 
            👤 Logged in as: <strong>{}</strong> | 
            🔑 Access: <strong>{}</strong></p>
        </div>
        """.format(
            current_user,
            "Administrator" if is_admin else ", ".join(domains).upper()
        ),
        unsafe_allow_html=True,
    )