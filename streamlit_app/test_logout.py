#!/usr/bin/env python3
"""
Simple test script to verify logout functionality
"""

import streamlit as st
import extra_streamlit_components as stx

def test_logout_functionality():
    """Test logout functionality"""
    st.title("🔧 Logout Functionality Test")
    
    # Display current session state
    st.subheader("Current Session State:")
    session_info = {
        "allow_access": st.session_state.get("allow_access", "Not set"),
        "current_user": st.session_state.get("current_user", "Not set"),
        "is_admin": st.session_state.get("is_admin", "Not set"),
        "domains": st.session_state.get("domains", "Not set"),
        "active_page": st.session_state.get("active_page", "Not set")
    }
    
    for key, value in session_info.items():
        st.write(f"**{key}:** {value}")
    
    st.markdown("---")
    
    # Manual login for testing
    st.subheader("🔐 Manual Login (for testing)")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Login as Admin", key="login_admin"):
            st.session_state.allow_access = 1
            st.session_state.current_user = "admin"
            st.session_state.is_admin = True
            st.session_state.domains = ["hr", "finance", "sales"]
            st.session_state.active_page = "Home"
            st.success("Logged in as Admin!")
            st.rerun()
    
    with col2:
        if st.button("Login as HR User", key="login_hr"):
            st.session_state.allow_access = 1
            st.session_state.current_user = "hr_user"
            st.session_state.is_admin = False
            st.session_state.domains = ["hr"]
            st.session_state.active_page = "Home"
            st.success("Logged in as HR User!")
            st.rerun()
    
    st.markdown("---")
    
    # Logout testing
    st.subheader("🚪 Logout Testing")
    
    if st.session_state.get("allow_access") == 1:
        st.success(f"✅ Currently logged in as: {st.session_state.get('current_user')}")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🚪 Simple Logout", key="simple_logout"):
                st.session_state.allow_access = 0
                st.session_state.current_user = None
                st.session_state.is_admin = False
                st.session_state.domains = []
                st.session_state.active_page = "Login"
                st.success("Simple logout completed!")
                st.rerun()
        
        with col2:
            if st.button("🧹 Clear All Session", key="clear_session"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.session_state.allow_access = 0
                st.session_state.active_page = "Login"
                st.success("All session data cleared!")
                st.rerun()
        
        with col3:
            if st.button("🍪 Clear Cookies", key="clear_cookies"):
                if 'test_cookie_manager' not in st.session_state:
                    st.session_state.test_cookie_manager = stx.CookieManager(key="test_cookie_manager")
                cookie_manager = st.session_state.test_cookie_manager
                try:
                    cookie_manager.delete("dq_session", key="test_clear")
                    st.success("Cookies cleared!")
                except Exception as e:
                    st.error(f"Cookie clear error: {e}")
    
    else:
        st.info("ℹ️ Not currently logged in")
    
    st.markdown("---")
    
    # Cookie testing
    st.subheader("🍪 Cookie Testing")
    if 'test_cookie_manager' not in st.session_state:
        st.session_state.test_cookie_manager = stx.CookieManager(key="test_cookie_manager")
    cookie_manager = st.session_state.test_cookie_manager
    
    try:
        current_cookie = cookie_manager.get("dq_session")
        if current_cookie:
            st.write(f"**Current Cookie:** {current_cookie[:50]}..." if len(current_cookie) > 50 else current_cookie)
        else:
            st.write("**Current Cookie:** None")
    except Exception as e:
        st.error(f"Cookie read error: {e}")
    
    # All session state keys
    st.subheader("🔍 All Session State Keys")
    if st.session_state:
        for key in st.session_state.keys():
            st.write(f"**{key}:** {st.session_state[key]}")
    else:
        st.write("No session state keys found")

if __name__ == "__main__":
    test_logout_functionality()
