import streamlit as st
from services.db import DatabaseConnection
from services.auth import AuthService
from session_manager import SessionManager

def show_admin_page():
    st.title("🔐 User Management")
    
    # Check if user is admin
    if not st.session_state.get("is_admin", False):
        st.error("You don't have permission to access this page.")
        return
    
    db = DatabaseConnection()
    auth_service = AuthService(db)
    
    tab1, tab2, tab3 = st.tabs(["👥 Users", "➕ Add User", "🔑 Permissions"])
    
    with tab1:
        show_users_list(db)
    
    with tab2:
        show_add_user_form(auth_service)
    
    with tab3:
        show_permissions_management(db, auth_service)

def show_users_list(db):
    st.subheader("User List")
    
    query = """
        SELECT user_id, username, email, full_name, is_admin, is_active, 
               created_at, last_login
        FROM users
        ORDER BY created_at DESC
    """
    
    users = db.execute_query(query)
    
    if users:
        import pandas as pd
        df = pd.DataFrame(users)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No users found.")

def show_add_user_form(auth_service):
    st.subheader("Create New User")
    
    with st.form("add_user_form"):
        username = st.text_input("Username*")
        email = st.text_input("Email*")
        full_name = st.text_input("Full Name")
        password = st.text_input("Password*", type="password")
        confirm_password = st.text_input("Confirm Password*", type="password")
        is_admin = st.checkbox("Administrator")
        
        submitted = st.form_submit_button("Create User")
        
        if submitted:
            if not username or not email or not password:
                st.error("Please fill in all required fields.")
            elif password != confirm_password:
                st.error("Passwords don't match.")
            elif len(password) < 8:
                st.error("Password must be at least 8 characters long.")
            else:
                user_id = auth_service.create_user(
                    username, email, password, full_name, is_admin
                )
                if user_id:
                    st.success(f"User '{username}' created successfully!")
                else:
                    st.error("Failed to create user. Username or email may already exist.")

def show_permissions_management(db, auth_service):
    st.subheader("Manage Permissions")
    
    # Select user
    users_query = "SELECT user_id, username, full_name FROM users WHERE is_active = TRUE ORDER BY username"
    users = db.execute_query(users_query)
    
    if not users:
        st.info("No users available.")
        return
    
    user_options = {f"{u['username']} ({u['full_name'] or 'No name'})": u['user_id'] 
                   for u in users}
    selected_user = st.selectbox("Select User", options=list(user_options.keys()))
    user_id = user_options[selected_user]
    
    # Display current permissions
    permissions = auth_service.get_user_permissions(user_id)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Current Permissions:**")
        if permissions['is_admin']:
            st.success("🔐 Administrator (Full Access)")
        else:
            if permissions['domains']:
                st.write("**Domain Access:**")
                for domain in permissions['domains']:
                    st.write(f"- {domain['domain_name']}")
            
            if permissions['tables']:
                st.write("**Table Access:**")
                for table in permissions['tables']:
                    st.write(f"- {table['domain_name']}.{table['schema_name']}.{table['table_name']}")
            
            if not permissions['domains'] and not permissions['tables']:
                st.warning("No permissions assigned")
    
    with col2:
        st.write("**Grant New Permission:**")
        
        permission_type = st.radio("Permission Type", 
                                   ["Domain Access", "Table Access"])
        
        if permission_type == "Domain Access":
            domains_query = "SELECT domain_name FROM domains ORDER BY domain_name"
            domains = db.execute_query(domains_query)
            domain_names = [d['domain_name'] for d in domains]
            
            selected_domain = st.selectbox("Select Domain", domain_names)
            
            if st.button("Grant Domain Access"):
                current_user = SessionManager.get_current_user()
                if auth_service.grant_domain_permission(
                    user_id, selected_domain, current_user['user_id']
                ):
                    st.success(f"Domain access granted!")
                    st.rerun()
        
        else:  # Table Access
            # Get domains
            domains_query = "SELECT domain_id, domain_name FROM domains ORDER BY domain_name"
            domains = db.execute_query(domains_query)
            domain_dict = {d['domain_name']: d['domain_id'] for d in domains}
            
            selected_domain = st.selectbox("Select Domain", list(domain_dict.keys()))
            domain_id = domain_dict[selected_domain]
            
            # Get tables for selected domain
            tables_query = """
                SELECT schema_name, table_name 
                FROM domain_tables 
                WHERE domain_id = %s
                ORDER BY schema_name, table_name
            """
            tables = db.execute_query(tables_query, (domain_id,))
            table_options = [f"{t['schema_name']}.{t['table_name']}" for t in tables]
            
            if table_options:
                selected_table = st.selectbox("Select Table", table_options)
                schema_name, table_name = selected_table.split('.')
                
                if st.button("Grant Table Access"):
                    current_user = SessionManager.get_current_user()
                    if auth_service.grant_table_permission(
                        user_id, selected_domain, schema_name, 
                        table_name, current_user['user_id']
                    ):
                        st.success(f"Table access granted!")
                        st.rerun()
            else:
                st.info("No tables found in this domain.")

if __name__ == "__main__":
    show_admin_page()