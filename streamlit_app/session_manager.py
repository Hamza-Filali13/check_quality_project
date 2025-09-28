"""
Centralized session management for the DQ Streamlit App
Handles authentication, session state, and cookies consistently
"""

import json
import time
import hmac
import hashlib
import streamlit as st
import extra_streamlit_components as stx
import yaml
from typing import Optional, Dict, Any

class SessionManager:
    """Centralized session management"""
    
    def __init__(self):
        self.app_secret = "eYkH3Qxk5a2yX2hYwC6KcRk1S0m9e2m1b7yP7s1pA9I="
        self.cookie_name = "dq_session"
        self.session_timeout = 24 * 3600  # 24 hours
        self._cookie_manager = None
        self.credentials = self._load_credentials()
        self._initialize_session()
    
    def _load_credentials(self):
        """Load credentials from YAML file"""
        try:
            with open("config/credentials.yml") as f:
                return yaml.safe_load(f)['users']
        except Exception as e:
            st.error(f"Error loading credentials: {e}")
            # Fallback to demo users if YAML fails
            return {
                "admin": {"name": "Admin User", "password": "admin", "domains": ["hr", "finance", "sales"]},
                "hr_user": {"name": "HR User", "password": "password", "domains": ["hr"]},
                "finance_user": {"name": "Finance User", "password": "password", "domains": ["finance"]},
                "sales_user": {"name": "Sales User", "password": "password", "domains": ["sales"]}
            }
    
    @property
    def cookie_manager(self):
        """Get cookie manager with lazy initialization"""
        if self._cookie_manager is None:
            try:
                self._cookie_manager = stx.CookieManager(key="global_cookie_manager")
            except Exception:
                pass  # Silent fail - app works without cookies
        return self._cookie_manager
    
    def _initialize_session(self):
        """Initialize session state with defaults (using original variable names)"""
        defaults = {
            "allow_access": 0,  # Original variable name
            "current_user": None,  # Original variable name
            "is_admin": False,
            "domains": [],
            "login_time": None,
            "active_page": "Login",  # Original variable name
            # Also initialize new variables for consistency
            "authenticated": False,
            "username": None,
            "page_refreshed": False
        }
        
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
    
    def _sign_data(self, data: str) -> str:
        """Sign data with HMAC"""
        return hmac.new(self.app_secret.encode(), data.encode(), hashlib.sha256).hexdigest()
    
    def _create_session_cookie(self, user_data: Dict[str, Any]) -> Optional[str]:
        """Create signed session cookie"""
        try:
            session_data = {
                "username": user_data["username"],
                "is_admin": user_data["is_admin"],
                "domains": user_data["domains"],
                "timestamp": time.time()
            }
            session_json = json.dumps(session_data)
            signature = self._sign_data(session_json)
            return f"{session_json}.{signature}"
        except Exception:
            return None
    
    def _validate_session_cookie(self, cookie_value: str) -> Optional[Dict[str, Any]]:
        """Validate and parse session cookie"""
        try:
            if not cookie_value or "." not in cookie_value:
                return None
            
            session_json, signature = cookie_value.rsplit(".", 1)
            
            # Verify signature
            if self._sign_data(session_json) != signature:
                return None
            
            # Parse data
            session_data = json.loads(session_json)
            
            # Check expiration
            if time.time() - session_data.get("timestamp", 0) > self.session_timeout:
                return None
            
            return session_data
        except Exception:
            return None
    
    def authenticate(self, username: str, password: str) -> bool:
        """Authenticate user against YAML credentials and create session"""
        if not username or not password:
            return False
        
        # Check credentials using the same logic as original login
        user = self.credentials.get(username)
        if not user or user["password"] != password:
            return False
        
        # Determine if user is admin (same logic as original)
        is_admin = username == 'admin'
        
        # Create session
        user_data = {
            "username": username,
            "name": user.get("name", username),
            "is_admin": is_admin,
            "domains": user["domains"]
        }
        
        # Update session state (using same variables as original)
        st.session_state.allow_access = 1  # Original used this instead of authenticated
        st.session_state.current_user = username  # Original variable name
        st.session_state.is_admin = is_admin
        st.session_state.domains = user["domains"]
        st.session_state.login_time = time.time()
        
        # Also set the new variables for consistency
        st.session_state.authenticated = True
        st.session_state.username = username
        
        # Create cookie using original signing method
        if self.cookie_manager:
            cookie_value = self._create_session_cookie(user_data)
            if cookie_value:
                try:
                    self.cookie_manager.set(self.cookie_name, cookie_value, key="session_set")
                except Exception:
                    pass  # Silent fail
        
        return True
    
    def restore_session(self) -> bool:
        """Restore session from cookie if valid"""
        if st.session_state.get("authenticated"):
            return True  # Already authenticated
        
        if not self.cookie_manager:
            return False
        
        try:
            cookie_value = self.cookie_manager.get(self.cookie_name)
            if not cookie_value:
                return False
            
            session_data = self._validate_session_cookie(cookie_value)
            if not session_data:
                return False
            
            # Restore session state (using both old and new variable names)
            st.session_state.allow_access = 1  # Original variable
            st.session_state.current_user = session_data["username"]  # Original variable
            st.session_state.is_admin = session_data["is_admin"]
            st.session_state.domains = session_data["domains"]
            st.session_state.login_time = session_data["timestamp"]
            
            # Also set new variables for consistency
            st.session_state.authenticated = True
            st.session_state.username = session_data["username"]
            
            return True
        except Exception:
            return False
    
    def logout(self):
        """Logout user and clear session"""
        # Clear session state (both old and new variables)
        st.session_state.allow_access = 0  # Original variable
        st.session_state.current_user = None  # Original variable
        st.session_state.is_admin = False
        st.session_state.domains = []
        st.session_state.login_time = None
        
        # Also clear new variables
        st.session_state.authenticated = False
        st.session_state.username = None
        
        # Clear cookie
        if self.cookie_manager:
            try:
                self.cookie_manager.delete(self.cookie_name, key="session_clear")
            except Exception:
                pass
        
        # Clear cache
        try:
            st.cache_data.clear()
        except Exception:
            pass
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated (check both old and new variables)"""
        return (st.session_state.get("authenticated", False) or 
                st.session_state.get("allow_access", 0) == 1)
    
    def get_user_info(self) -> Dict[str, Any]:
        """Get current user information (use original variable names)"""
        return {
            "username": st.session_state.get("current_user") or st.session_state.get("username"),
            "is_admin": st.session_state.get("is_admin", False),
            "domains": st.session_state.get("domains", []),
            "login_time": st.session_state.get("login_time")
        }
    
    def require_auth(self, redirect_to_login: bool = True) -> bool:
        """Require authentication, optionally redirect to login"""
        if not self.restore_session():
            if redirect_to_login:
                st.session_state.page = "login"
            return False
        return True

# Global session manager instance
@st.cache_resource
def get_session_manager():
    return SessionManager()

session_manager = get_session_manager()
