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
from typing import Optional, Dict, Any
from services.db import DatabaseConnection
from services.auth import AuthService

class SessionManager:
    """Centralized session management with database authentication"""
    
    def __init__(self):
        self.app_secret = "eYkH3Qxk5a2yX2hYwC6KcRk1S0m9e2m1b7yP7s1pA9I="
        self.cookie_name = "dq_session"
        self.session_timeout = 24 * 3600  # 24 hours
        self._cookie_manager = None
        self._db = None
        self._auth_service = None
        self._initialize_session()
    
    @property
    def db(self):
        """Lazy load database connection"""
        if self._db is None:
            self._db = DatabaseConnection()
        return self._db
    
    @property
    def auth_service(self):
        """Lazy load auth service"""
        if self._auth_service is None:
            self._auth_service = AuthService(self.db)
        return self._auth_service
    
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
        """Initialize session state with defaults"""
        defaults = {
            "allow_access": 0,  # 0 = not authenticated, 1 = authenticated
            "current_user": None,
            "user_id": None,
            "is_admin": False,
            "domains": [],
            "permissions": None,
            "login_time": None,
            "active_page": "Login",
            "authenticated": False,
            "username": None,
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
                "user_id": user_data["user_id"],
                "username": user_data["username"],
                "is_admin": user_data["is_admin"],
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
    
    def _extract_domains_from_permissions(self, permissions: Dict) -> list:
        """Extract unique domain names from permissions structure"""
        domain_set = set()
        
        st.info(f"DEBUG _extract: Starting extraction")
        st.info(f"DEBUG _extract: permissions type = {type(permissions)}")
        st.info(f"DEBUG _extract: permissions keys = {permissions.keys() if permissions else 'None'}")
        
        # From domain-level permissions
        if permissions.get('domains'):
            st.info(f"DEBUG _extract: Found {len(permissions['domains'])} domain permissions")
            for idx, domain in enumerate(permissions['domains']):
                st.info(f"DEBUG _extract: Domain {idx}: {domain} (type: {type(domain)})")
                if isinstance(domain, dict) and 'domain_name' in domain:
                    domain_set.add(domain['domain_name'])
                    st.success(f"DEBUG _extract: Added domain: {domain['domain_name']}")
        else:
            st.warning("DEBUG _extract: No domain permissions found")
        
        # From table-level permissions
        if permissions.get('tables'):
            st.info(f"DEBUG _extract: Found {len(permissions['tables'])} table permissions")
            for idx, table in enumerate(permissions['tables']):
                st.info(f"DEBUG _extract: Table {idx}: {table} (type: {type(table)})")
                if isinstance(table, dict) and 'domain_name' in table:
                    domain_set.add(table['domain_name'])
                    st.success(f"DEBUG _extract: Added domain from table: {table['domain_name']}")
        else:
            st.warning("DEBUG _extract: No table permissions found")
        
        result = sorted(list(domain_set))
        st.success(f"DEBUG _extract: Final domain_set: {result}")
        return result
    
    def authenticate(self, username: str, password: str) -> bool:
        """Authenticate user against database and create session"""
        if not username or not password:
            return False
        
        # Authenticate with database
        user = self.auth_service.authenticate(username, password)
        if not user:
            return False
        
        # Get permissions
        permissions = self.auth_service.get_user_permissions(user['user_id'])
        
        # Extract accessible domains
        domains = []
        if permissions['is_admin']:
            # Admin has access to all domains - get from database
            query = "SELECT domain_name FROM domains ORDER BY domain_name"
            domain_results = self.db.execute_query(query)
            domains = [d['domain_name'] for d in domain_results]
        else:
            # Extract domains from permissions
            domains = self._extract_domains_from_permissions(permissions)
        
        # Update session state
        st.session_state.allow_access = 1
        st.session_state.current_user = username
        st.session_state.user_id = user['user_id']
        st.session_state.is_admin = user['is_admin']
        st.session_state.domains = domains
        st.session_state.permissions = permissions
        st.session_state.login_time = time.time()
        st.session_state.authenticated = True
        st.session_state.username = username
        
        # Create cookie
        if self.cookie_manager:
            cookie_value = self._create_session_cookie(user)
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
            
            # Get fresh user permissions from database
            user_id = session_data['user_id']
            permissions = self.auth_service.get_user_permissions(user_id)
            
            # Extract domains
            domains = []
            if permissions['is_admin']:
                query = "SELECT domain_name FROM domains ORDER BY domain_name"
                domain_results = self.db.execute_query(query)
                domains = [d['domain_name'] for d in domain_results]
            else:
                domains = self._extract_domains_from_permissions(permissions)
            
            # Restore session state
            st.session_state.allow_access = 1
            st.session_state.current_user = session_data["username"]
            st.session_state.user_id = user_id
            st.session_state.is_admin = session_data["is_admin"]
            st.session_state.domains = domains
            st.session_state.permissions = permissions
            st.session_state.login_time = session_data["timestamp"]
            st.session_state.authenticated = True
            st.session_state.username = session_data["username"]
            
            return True
        except Exception:
            return False
    
    def logout(self):
        """Logout user and clear session"""
        # Clear session state
        st.session_state.allow_access = 0
        st.session_state.current_user = None
        st.session_state.user_id = None
        st.session_state.is_admin = False
        st.session_state.domains = []
        st.session_state.permissions = None
        st.session_state.login_time = None
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
        """Check if user is authenticated"""
        return (st.session_state.get("authenticated", False) or 
                st.session_state.get("allow_access", 0) == 1)
    
    def get_user_info(self) -> Dict[str, Any]:
        """Get current user information"""
        return {
            "user_id": st.session_state.get("user_id"),
            "username": st.session_state.get("current_user") or st.session_state.get("username"),
            "is_admin": st.session_state.get("is_admin", False),
            "domains": st.session_state.get("domains", []),
            "permissions": st.session_state.get("permissions"),
            "login_time": st.session_state.get("login_time")
        }
    
    def has_domain_access(self, domain_name: str) -> bool:
        """Check if current user has access to domain"""
        if not self.is_authenticated():
            return False
        
        user_id = st.session_state.get("user_id")
        if not user_id:
            return False
        
        return self.auth_service.has_domain_access(user_id, domain_name)
    
    def filter_domains_by_access(self, domains: list) -> list:
        """Filter domains list based on user permissions"""
        if not self.is_authenticated():
            return []
        
        permissions = st.session_state.get("permissions")
        if not permissions:
            return []
        
        if permissions['is_admin']:
            return domains
        
        accessible_domains = set(st.session_state.get("domains", []))
        return [d for d in domains if d in accessible_domains]

# Global session manager instance
@st.cache_resource
def get_session_manager():
    return SessionManager()

session_manager = get_session_manager()