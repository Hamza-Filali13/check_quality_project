import streamlit as st
import base64
import time
from session_manager import session_manager

def run():
    """Login page with modern UI"""
    
    # Helper function to get base64 of image
    @st.cache_data
    def get_base64_of_bin_file(path: str) -> str:
        try:
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode()
        except Exception:
            return ""
    
    # Modern login page styling
    st.markdown("""
    <style>
    /* Reset and minimal spacing */
    .main .block-container {
        padding: 0 !important;
        max-width: none !important;
        margin-top: 0 !important;
    }
    
    .stApp > div:first-child {
        padding-top: 0 !important;
        margin-top: 0 !important;
    }
    

    
    .login-logo {
        width: 120px;
        height: 120px;
        border-radius: 50%;
        margin: 0 auto 2rem auto;
        display: block;
        border: 4px solid #667eea;
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
    }
    
    .login-title {
        color: #2d3748;
        font-size: 2.2rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
        background: linear-gradient(135deg, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .login-subtitle {
        color: #718096;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    
    /* Form styling */
    .stTextInput > div > div > input {
        border: 2px solid #e2e8f0;
        border-radius: 12px;
        padding: 1rem;
        font-size: 1rem;
        transition: all 0.3s ease;
        background: #f8fafc;
        height:100%;
        width:100%;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        background: white;
    }
    
    .stButton > button {
        width: 100%;
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 1rem 2rem;
        font-size: 1.1rem;
        font-weight: 600;
        transition: all 0.3s ease;
        margin-top: 1rem;
    }
    
    .stButton > button:hover {
        transform: translateY(-3px);
        box-shadow: 0 15px 35px rgba(102, 126, 234, 0.4);
    }
    
    /* Demo credentials styling */
    .demo-credentials {
        background: linear-gradient(135deg, #f093fb, #f5576c);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        margin-top: 2rem;
        box-shadow: 0 8px 25px rgba(240, 147, 251, 0.3);
    }
    
    .demo-credentials h4 {
        margin-bottom: 1rem;
        font-weight: 600;
    }
    
    .demo-credentials code {
        background: rgba(255, 255, 255, 0.2);
        padding: 0.3rem 0.6rem;
        border-radius: 6px;
        font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Background image (if available)
    bg_str = get_base64_of_bin_file('logos/image.png')
    if bg_str:
        st.markdown(f"""
        <style>
        .login-container {{
            background-image: url("data:image/png;base64,{bg_str}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
        }}
        </style>
        """, unsafe_allow_html=True)
    
    # Main login container
    # st.markdown('<div class="login-container">', unsafe_allow_html=True)
    c1, c2, c3, = st.columns([1, 2, 1])
    st.markdown('<div class="login-card">', unsafe_allow_html=True)
    
    # Logo
    
    # Title and subtitle
    
    # Login form
    with c2:
        logo_str = get_base64_of_bin_file('logos/icon.jpg')
        if not logo_str:
            logo_str = get_base64_of_bin_file('logos/img/FollowU.png')
        
        if logo_str:
            st.markdown(f'<img src="data:image/png;base64,{logo_str}" class="login-logo" alt="DXC Logo">', unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="width: 120px; height: 120px; background: linear-gradient(135deg, #667eea, #764ba2); 
            border-radius: 50%; margin: 0 auto 2rem auto; display: flex; align-items: center; 
            justify-content: center; font-size: 3rem; color: white; border: 4px solid #667eea;">📊</div>
            """, unsafe_allow_html=True)
        
        st.markdown('<h1 class="login-title">DXC Data Quality Platform</h1>', unsafe_allow_html=True)
        st.markdown('<p class="login-subtitle">Sign in to access your data quality dashboard</p>', unsafe_allow_html=True)
    
        with c2.form("login_form", clear_on_submit=False):
            st.markdown("### 🔐 Authentication")
            username = st.text_input("👤 Username", placeholder="Enter your username", key="login_username")
            password = st.text_input("🔒 Password", type="password", placeholder="Enter your password", key="login_password")
            
            submitted = st.form_submit_button("🚀 Sign In")
            
            if submitted:
                if username and password:
                    with st.spinner("Authenticating..."):
                        if session_manager.authenticate(username, password):
                            st.success("✅ Login successful! Welcome to the platform!")
                            # st.balloons()  # Celebration animation
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ Invalid username or password. Please try again.")
                else:
                    st.warning("⚠️ Please enter both username and password.")
        

         
         # Get credentials from session manager
        # credentials = session_manager.credentials
        
        # for username, user_data in credentials.items():
        #     name = user_data.get('name', username)
        #     domains = ', '.join(user_data.get('domains', []))
        #     is_admin_user = username == 'admin'
            
        #     role_badge = "🔑 Administrator" if is_admin_user else f"👤 {domains.upper()}"
            
        #     st.markdown(f"""
        #     <div style="background: #f8fafc; padding: 1rem; border-radius: 8px; margin: 0.5rem 0; border-left: 4px solid #667eea;">
        #         <strong>{role_badge}</strong><br>
        #         <strong>Name:</strong> {name}<br>
        #         <strong>Username:</strong> <code>{username}</code> | 
        #         <strong>Password:</strong> <code>{user_data['password']}</code><br>
        #         <strong>Access:</strong> {domains}
        #     </div>
        #     """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)  # Close login-card
        st.markdown('</div>', unsafe_allow_html=True)  # Close login-container
    
    st.markdown("""<style>
    .css-krjigr .css-1ixxbn0{
            gap: 0rem;
        }

    </style> """, unsafe_allow_html=True)
    st.markdown(
        """<br><br><center><div class="css-qri22k egzxvld4">Copyrights <a href="//https://dxc.com" class="css-1vbd788 egzxvld3">DXC Technologie</a> @ 2025</div></center>""",
        unsafe_allow_html=True)
