import pandas as pd
from sqlalchemy import create_engine
import streamlit as st
import yaml
import os
from pathlib import Path

def load_db_config():
    """Load database config from Streamlit secrets, YAML file, or environment variables"""
    
    # Priority 1: Try Streamlit secrets (best for production/cloud)
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
    
    # Priority 3: Environment variables (fallback)
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
        return create_engine(connection_string)
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

def run_query_with_params(query: str, params: tuple) -> pd.DataFrame:
    """Run parameterized SQL query and return as DataFrame"""
    try:
        engine = get_mysql_engine()
        with engine.connect() as conn:
            return pd.read_sql(query, conn, params=params)
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