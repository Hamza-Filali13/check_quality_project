import pandas as pd
from sqlalchemy import create_engine
import yaml
import os

# Load DB config from YAML or env
CONFIG_PATH = "config/settings.yml"

with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)

DB_CFG = config["database"]

def get_mysql_engine():
    """Create a MySQL SQLAlchemy engine"""
    return create_engine(
        f"mysql+pymysql://{DB_CFG['user']}:{DB_CFG['password']}@{DB_CFG['host']}:{DB_CFG['port']}/{DB_CFG['database']}"
    )

def run_query(query: str) -> pd.DataFrame:
    """Run SQL query and return as DataFrame"""
    engine = get_mysql_engine()
    with engine.connect() as conn:
        return pd.read_sql(query, conn)

def run_query_with_params(query: str, params: tuple) -> pd.DataFrame:
    """Run parameterized SQL query and return as DataFrame"""
    engine = get_mysql_engine()
    with engine.connect() as conn:
        return pd.read_sql(query, conn, params=params)

def execute_query(query: str, params: tuple = None) -> pd.DataFrame:
    """Execute SQL query with optional parameters and return as DataFrame"""
    engine = get_mysql_engine()
    with engine.connect() as conn:
        if params:
            return pd.read_sql(query, conn, params=params)
        else:
            return pd.read_sql(query, conn)
