import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import streamlit as st
import yaml
import os
from pathlib import Path
from typing import Optional, List, Dict, Any

def load_db_config():
    """Load database config from Streamlit secrets, YAML file, or environment variables"""
    
    # Priority 1: Try Streamlit secrets
    try:
        if hasattr(st, 'secrets') and 'database' in st.secrets:
            return dict(st.secrets['database'])
    except Exception:
        pass
    
    # Priority 2: Try YAML config file
    config_paths = [
        Path("config/settings.yml"),
        Path("./config/settings.yml"),
        Path(__file__).parent.parent / "config" / "settings.yml",
    ]
    
    for config_path in config_paths:
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    config = yaml.safe_load(f)
                    if config and "database" in config:
                        return config["database"]
            except Exception as e:
                st.warning(f"Could not load config from {config_path}: {e}")
    
    # Priority 3: Environment variables
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", 3306)),
        "database": os.getenv("DB_NAME", "dq_database"),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", "password")
    }

# Load configuration
DB_CFG = load_db_config()

def get_mysql_engine():
    """Create a MySQL SQLAlchemy engine"""
    try:
        connection_string = (
            f"mysql+pymysql://{DB_CFG['user']}:{DB_CFG['password']}"
            f"@{DB_CFG['host']}:{DB_CFG['port']}/{DB_CFG['database']}"
        )
        return create_engine(connection_string, pool_pre_ping=True)
    except KeyError as e:
        st.error(f"Missing database configuration: {e}")
        raise

def run_query(query: str) -> pd.DataFrame:
    """Run SQL query and return as DataFrame"""
    try:
        engine = get_mysql_engine()
        with engine.connect() as conn:
            return pd.read_sql(query, conn)
    except Exception as e:
        st.error(f"Database query error: {e}")
        return pd.DataFrame()

def execute_query(query: str, params: tuple = None) -> pd.DataFrame:
    """Execute SQL query with optional parameters and return as DataFrame"""
    try:
        engine = get_mysql_engine()
        with engine.connect() as conn:
            if params:
                return pd.read_sql(query, conn, params=params)
            else:
                return pd.read_sql(query, conn)
    except Exception as e:
        st.error(f"Database query error: {e}")
        return pd.DataFrame()

def run_query_with_params(query: str, params: tuple) -> pd.DataFrame:
    """Run parameterized SQL query and return as DataFrame"""
    try:
        engine = get_mysql_engine()
        with engine.connect() as conn:
            return pd.read_sql(query, conn, params=params)
    except Exception as e:
        st.error(f"Database query error: {e}")
        return pd.DataFrame()


class DatabaseConnection:
    """Enhanced database connection class for authentication and user management"""
    
    def __init__(self):
        self.config = load_db_config()
        self._engine = None
    
    @property
    def engine(self):
        """Lazy load database engine"""
        if self._engine is None:
            self._engine = get_mysql_engine()
        return self._engine
    
    def execute_query(self, query: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Execute a query and return results as list of dictionaries
        Params should be a dict like {'username': 'admin', 'user_id': 1}
        Query should use named parameters like :username, :user_id
        """
        try:
            with self.engine.begin() as conn:  # Use begin() for automatic commit/rollback
                # Execute with named parameters
                result = conn.execute(text(query), params or {})
                
                # For SELECT queries that return rows
                if result.returns_rows:
                    columns = result.keys()
                    rows = result.fetchall()
                    return [dict(zip(columns, row)) for row in rows]
                else:
                    # For INSERT/UPDATE/DELETE - already committed by begin()
                    return []
        except SQLAlchemyError as e:
            st.error(f"Database error: {e}")
            import traceback
            st.error(f"Traceback: {traceback.format_exc()}")
            return []
        except Exception as e:
            st.error(f"Unexpected error: {e}")
            import traceback
            st.error(f"Traceback: {traceback.format_exc()}")
            return []

    
    def execute_select(self, query: str, params: Dict[str, Any] = None) -> pd.DataFrame:
        """Execute SELECT query and return as DataFrame"""
        try:
            with self.engine.connect() as conn:
                return pd.read_sql(text(query), conn, params=params or {})
        except Exception as e:
            st.error(f"Database query error: {e}")
            return pd.DataFrame()
    
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            st.error(f"Connection test failed: {e}")
            return False