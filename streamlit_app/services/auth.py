import bcrypt
from datetime import datetime
from typing import Optional, Dict, List
import streamlit as st
from services.db import DatabaseConnection

class AuthService:
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
        self.secret_key = st.secrets.get("jwt_secret_key", "your-secret-key-change-in-production")
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        except Exception:
            return False
    
    def authenticate(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate a user and return user info"""
        query = """
            SELECT user_id, username, email, full_name, is_admin, is_active, password_hash
            FROM users
            WHERE username = :username AND is_active = TRUE
        """
        
        result = self.db.execute_query(query, {'username': username})
        
        if not result:
            return None
        
        user = result[0]
        
        if not self.verify_password(password, user['password_hash']):
            return None
        
        # Update last login
        update_query = """
            UPDATE users 
            SET last_login = NOW() 
            WHERE user_id = :user_id
        """
        self.db.execute_query(update_query, {'user_id': user['user_id']})
        
        # Remove password_hash from returned user object
        user.pop('password_hash', None)
        
        return user
    
    def get_user_permissions(self, user_id: int) -> Dict:
        """Get all permissions for a user"""
        # Check if admin
        admin_query = "SELECT is_admin FROM users WHERE user_id = :user_id"
        admin_result = self.db.execute_query(admin_query, {'user_id': user_id})
        
        if admin_result and admin_result[0]['is_admin']:
            return {
                'is_admin': True,
                'has_full_access': True,
                'domains': [],
                'tables': []
            }
        
        # Get domain permissions
        domain_query = """
            SELECT d.domain_name, d.domain_id
            FROM user_domain_permissions udp
            JOIN domains d ON udp.domain_id = d.domain_id
            WHERE udp.user_id = :user_id
        """
        domains = self.db.execute_query(domain_query, {'user_id': user_id})
        
        # Get table permissions
        table_query = """
            SELECT d.domain_name, dt.schema_name, dt.table_name, dt.table_id, d.domain_id
            FROM user_table_permissions utp
            JOIN domain_tables dt ON utp.table_id = dt.table_id
            JOIN domains d ON dt.domain_id = d.domain_id
            WHERE utp.user_id = :user_id
        """
        tables = self.db.execute_query(table_query, {'user_id': user_id})
        
        return {
            'is_admin': False,
            'has_full_access': False,
            'domains': domains or [],
            'tables': tables or []
        }
    
    # ... rest of your methods stay the same ...
    
    def get_accessible_domains(self, user_id: int) -> List[str]:
        """Get list of domain names user can access"""
        permissions = self.get_user_permissions(user_id)
        
        if permissions['is_admin']:
            query = "SELECT domain_name FROM domains ORDER BY domain_name"
            results = self.db.execute_query(query)
            return [r['domain_name'] for r in results]
        
        # Collect unique domains from both domain and table permissions
        domain_set = set()
        for domain in permissions['domains']:
            domain_set.add(domain['domain_name'])
        for table in permissions['tables']:
            domain_set.add(table['domain_name'])
        
        return sorted(list(domain_set))
    
    def get_accessible_tables(self, user_id: int, domain_name: str = None) -> List[Dict]:
        """Get list of tables user can access, optionally filtered by domain"""
        permissions = self.get_user_permissions(user_id)
        
        # Admin gets all tables
        if permissions['is_admin']:
            query = """
                SELECT dt.table_id, dt.schema_name, dt.table_name, d.domain_name, d.domain_id
                FROM domain_tables dt
                JOIN domains d ON dt.domain_id = d.domain_id
            """
            params = {}
            if domain_name:
                query += " WHERE d.domain_name = :domain_name"
                params['domain_name'] = domain_name
            query += " ORDER BY d.domain_name, dt.schema_name, dt.table_name"
            return self.db.execute_query(query, params)
        
        # Collect accessible tables
        accessible_tables = []
        
        # From domain-level permissions (all tables in domain)
        for domain in permissions['domains']:
            if not domain_name or domain['domain_name'] == domain_name:
                query = """
                    SELECT dt.table_id, dt.schema_name, dt.table_name, 
                           d.domain_name, d.domain_id
                    FROM domain_tables dt
                    JOIN domains d ON dt.domain_id = d.domain_id
                    WHERE d.domain_id = :domain_id
                """
                tables = self.db.execute_query(query, {'domain_id': domain['domain_id']})
                accessible_tables.extend(tables)
        
        # From table-level permissions
        for table in permissions['tables']:
            if not domain_name or table['domain_name'] == domain_name:
                accessible_tables.append(table)
        
        # Remove duplicates based on table_id
        seen = set()
        unique_tables = []
        for table in accessible_tables:
            if table['table_id'] not in seen:
                seen.add(table['table_id'])
                unique_tables.append(table)
        
        return sorted(unique_tables, key=lambda x: (x['domain_name'], x['schema_name'], x['table_name']))
    
    def has_domain_access(self, user_id: int, domain_name: str) -> bool:
        """Check if user has access to a specific domain"""
        accessible_domains = self.get_accessible_domains(user_id)
        return domain_name in accessible_domains
    
    def has_table_access(self, user_id: int, domain_name: str, 
                        schema_name: str, table_name: str) -> bool:
        """Check if user has access to a specific table"""
        permissions = self.get_user_permissions(user_id)
        
        if permissions['is_admin']:
            return True
        
        # Check domain-level permissions
        for domain in permissions['domains']:
            if domain['domain_name'] == domain_name:
                return True
        
        # Check table-level permissions
        for table in permissions['tables']:
            if (table['domain_name'] == domain_name and 
                table['schema_name'] == schema_name and 
                table['table_name'] == table_name):
                return True
        
        return False
    
    def create_user(self, username: str, email: str, password: str, 
                    full_name: str = None, is_admin: bool = False, 
                    created_by: int = None) -> Optional[int]:
        """Create a new user"""
        password_hash = self.hash_password(password)
        
        query = """
            INSERT INTO users (username, email, password_hash, full_name, is_admin)
            VALUES (:username, :email, :password_hash, :full_name, :is_admin)
        """
        
        try:
            self.db.execute_query(query, {
                'username': username,
                'email': email,
                'password_hash': password_hash,
                'full_name': full_name,
                'is_admin': is_admin
            })
            
            # Get the created user's ID
            user_query = "SELECT user_id FROM users WHERE username = :username"
            result = self.db.execute_query(user_query, {'username': username})
            return result[0]['user_id'] if result else None
        except Exception as e:
            st.error(f"Error creating user: {e}")
            return None
    
    def update_user(self, user_id: int, **kwargs) -> bool:
        """Update user information"""
        allowed_fields = ['email', 'full_name', 'is_admin', 'is_active']
        updates = []
        params = {'user_id': user_id}
        
        for field, value in kwargs.items():
            if field in allowed_fields:
                updates.append(f"{field} = :{field}")
                params[field] = value
        
        if not updates:
            return False
        
        query = f"UPDATE users SET {', '.join(updates)} WHERE user_id = :user_id"
        
        try:
            self.db.execute_query(query, params)
            return True
        except Exception as e:
            st.error(f"Error updating user: {e}")
            return False
    
    def grant_domain_permission(self, user_id: int, domain_name: str, 
                               granted_by: int) -> bool:
        """Grant domain-level permission to a user"""
        query = """
            INSERT INTO user_domain_permissions (user_id, domain_id, granted_by)
            SELECT :user_id, domain_id, :granted_by
            FROM domains
            WHERE domain_name = :domain_name
            ON DUPLICATE KEY UPDATE granted_at = NOW()
        """
        
        try:
            self.db.execute_query(query, {
                'user_id': user_id,
                'granted_by': granted_by,
                'domain_name': domain_name
            })
            return True
        except Exception as e:
            st.error(f"Error granting domain permission: {e}")
            return False
    
    def revoke_domain_permission(self, user_id: int, domain_name: str) -> bool:
        """Revoke domain-level permission from a user"""
        query = """
            DELETE udp FROM user_domain_permissions udp
            JOIN domains d ON udp.domain_id = d.domain_id
            WHERE udp.user_id = :user_id AND d.domain_name = :domain_name
        """
        
        try:
            self.db.execute_query(query, {
                'user_id': user_id,
                'domain_name': domain_name
            })
            return True
        except Exception as e:
            st.error(f"Error revoking domain permission: {e}")
            return False
    
    def grant_table_permission(self, user_id: int, table_id: int, 
                              granted_by: int) -> bool:
        """Grant table-level permission to a user"""
        query = """
            INSERT INTO user_table_permissions (user_id, table_id, granted_by)
            VALUES (:user_id, :table_id, :granted_by)
            ON DUPLICATE KEY UPDATE granted_at = NOW()
        """
        
        try:
            self.db.execute_query(query, {
                'user_id': user_id,
                'table_id': table_id,
                'granted_by': granted_by
            })
            return True
        except Exception as e:
            st.error(f"Error granting table permission: {e}")
            return False
    
    def revoke_table_permission(self, user_id: int, table_id: int) -> bool:
        """Revoke table-level permission from a user"""
        query = """
            DELETE FROM user_table_permissions
            WHERE user_id = :user_id AND table_id = :table_id
        """
        
        try:
            self.db.execute_query(query, {
                'user_id': user_id,
                'table_id': table_id
            })
            return True
        except Exception as e:
            st.error(f"Error revoking table permission: {e}")
            return False
    
    def get_all_users(self) -> List[Dict]:
        """Get all users with their basic info"""
        query = """
            SELECT user_id, username, email, full_name, is_admin, is_active, 
                   created_at, last_login
            FROM users
            ORDER BY username
        """
        return self.db.execute_query(query)