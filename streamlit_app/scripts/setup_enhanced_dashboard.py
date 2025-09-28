#!/usr/bin/env python3
"""
Setup script for Enhanced Data Quality Dashboard
Initializes database, generates sample data, and configures the system
"""

import os
import sys
import subprocess
import time
import psycopg2
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are available"""
    print("🔍 Checking dependencies...")
    
    required_packages = [
        "streamlit", "plotly", "pandas", "psycopg2", 
        "requests", "numpy", "openpyxl"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing packages: {', '.join(missing_packages)}")
        print("📦 Installing missing packages...")
        
        for package in missing_packages:
            subprocess.run([sys.executable, "-m", "pip", "install", package], 
                         check=True, capture_output=True)
        
        print("✅ All packages installed successfully!")
    else:
        print("✅ All dependencies are available!")

def wait_for_database(max_retries=30, delay=2):
    """Wait for database to be ready"""
    print("⏳ Waiting for database to be ready...")
    
    db_config = {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "dbname": os.getenv("POSTGRES_DB", "dq_db"),
        "user": os.getenv("POSTGRES_USER", "postgres"),
        "password": os.getenv("POSTGRES_PASSWORD", "postgres")
    }
    
    for attempt in range(max_retries):
        try:
            conn = psycopg2.connect(**db_config)
            conn.close()
            print("✅ Database is ready!")
            return True
        except psycopg2.OperationalError:
            if attempt < max_retries - 1:
                print(f"⏳ Database not ready, retrying in {delay}s... ({attempt + 1}/{max_retries})")
                time.sleep(delay)
            else:
                print("❌ Database connection failed after maximum retries")
                return False
    
    return False

def setup_database():
    """Setup database schemas and tables"""
    print("🗄️ Setting up database...")
    
    db_config = {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "dbname": os.getenv("POSTGRES_DB", "dq_db"),
        "user": os.getenv("POSTGRES_USER", "postgres"),
        "password": os.getenv("POSTGRES_PASSWORD", "postgres")
    }
    
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        # Create schemas
        schemas = ["dbt"]
        for schema in schemas:
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
            print(f"✅ Created schema: {schema}")
        
        # Create enhanced tables
        tables_sql = [
            """
            CREATE TABLE IF NOT EXISTS dbt.dq_test_results (
                id SERIAL PRIMARY KEY,
                table_name TEXT NOT NULL,
                column_name TEXT NOT NULL,
                test_name TEXT NOT NULL,
                test_type TEXT DEFAULT 'generic',
                status TEXT NOT NULL CHECK (status IN ('pass', 'fail', 'unknown')),
                score NUMERIC(5,2) CHECK (score >= 0 AND score <= 100),
                domain TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS dbt.dq_score (
                id SERIAL PRIMARY KEY,
                table_name TEXT NOT NULL,
                dq_score NUMERIC(5,2) CHECK (dq_score >= 0 AND dq_score <= 100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata JSONB
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS dbt.dq_issues (
                id SERIAL PRIMARY KEY,
                table_name TEXT NOT NULL,
                column_name TEXT,
                issue_type TEXT NOT NULL,
                description TEXT,
                severity TEXT CHECK (severity IN ('Critical', 'High', 'Medium', 'Low')),
                status TEXT DEFAULT 'Open' CHECK (status IN ('Open', 'In Progress', 'Resolved', 'Closed')),
                assigned_to TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP,
                metadata JSONB
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS dbt.dq_audit_log (
                id SERIAL PRIMARY KEY,
                user_name TEXT NOT NULL,
                action TEXT NOT NULL,
                table_name TEXT,
                details JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        ]
        
        for sql in tables_sql:
            cursor.execute(sql)
        
        # Create indexes for better performance
        indexes_sql = [
            "CREATE INDEX IF NOT EXISTS idx_test_results_table_name ON dbt.dq_test_results(table_name)",
            "CREATE INDEX IF NOT EXISTS idx_test_results_domain ON dbt.dq_test_results(domain)",
            "CREATE INDEX IF NOT EXISTS idx_test_results_status ON dbt.dq_test_results(status)",
            "CREATE INDEX IF NOT EXISTS idx_test_results_created_at ON dbt.dq_test_results(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_score_table_name ON dbt.dq_score(table_name)",
            "CREATE INDEX IF NOT EXISTS idx_score_created_at ON dbt.dq_score(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_issues_status ON dbt.dq_issues(status)",
            "CREATE INDEX IF NOT EXISTS idx_issues_severity ON dbt.dq_issues(severity)"
        ]
        
        for sql in indexes_sql:
            cursor.execute(sql)
        
        conn.commit()
        print("✅ Database setup completed successfully!")
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
    
    return True

def generate_sample_data():
    """Generate sample data for demonstration"""
    print("📊 Generating sample data...")
    
    script_path = Path(__file__).parent / "generate_sample_data.py"
    
    if script_path.exists():
        try:
            subprocess.run([sys.executable, str(script_path)], check=True)
            print("✅ Sample data generated successfully!")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Sample data generation failed: {e}")
            return False
    else:
        print("⚠️ Sample data generator not found, skipping...")
        return True

def create_config_files():
    """Create configuration files if they don't exist"""
    print("⚙️ Creating configuration files...")
    
    config_dir = Path(__file__).parent / "."
    
    # Create credentials.yaml if it doesn't exist
    credentials_file = config_dir / "credentials.yaml"
    if not credentials_file.exists():
        credentials_content = """
users:
  admin:
    name: "Administrator"
    password: "admin123"
    domains: ["hr", "finance", "sales"]
  
  hr_user:
    name: "HR Manager"
    password: "hr123"
    domains: ["hr"]
  
  finance_user:
    name: "Finance Manager"
    password: "finance123"
    domains: ["finance"]
  
  sales_user:
    name: "Sales Manager"
    password: "sales123"
    domains: ["sales"]
"""
        
        with open(credentials_file, 'w') as f:
            f.write(credentials_content)
        
        print("✅ Created credentials.yaml")
    
    # Create logs directory
    logs_dir = config_dir.parent / "logs"
    logs_dir.mkdir(exist_ok=True)
    (logs_dir / "streamlit").mkdir(exist_ok=True)
    (logs_dir / "postgres").mkdir(exist_ok=True)
    
    print("✅ Configuration files created!")

def check_services():
    """Check if required services are running"""
    print("🔍 Checking services...")
    
    # Check if running in Docker
    if os.path.exists("/.dockerenv"):
        print("🐳 Running inside Docker container")
        return True
    
    # Check if services are accessible
    services_ok = True
    
    # Check database
    try:
        db_config = {
            "host": os.getenv("POSTGRES_HOST", "localhost"),
            "port": int(os.getenv("POSTGRES_PORT", "5432")),
            "dbname": os.getenv("POSTGRES_DB", "dq_db"),
            "user": os.getenv("POSTGRES_USER", "postgres"),
            "password": os.getenv("POSTGRES_PASSWORD", "postgres")
        }
        
        conn = psycopg2.connect(**db_config)
        conn.close()
        print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        services_ok = False
    
    return services_ok

def main():
    """Main setup function"""
    print("🚀 Setting up Enhanced Data Quality Dashboard...")
    print("=" * 50)
    
    try:
        # Step 1: Check dependencies
        check_dependencies()
        
        # Step 2: Create configuration files
        create_config_files()
        
        # Step 3: Wait for database
        if not wait_for_database():
            print("❌ Setup failed: Database not available")
            sys.exit(1)
        
        # Step 4: Setup database
        if not setup_database():
            print("❌ Setup failed: Database setup error")
            sys.exit(1)
        
        # Step 5: Generate sample data
        generate_sample_data()
        
        # Step 6: Check services
        if not check_services():
            print("⚠️ Some services may not be fully available")
        
        print("=" * 50)
        print("🎉 Enhanced Data Quality Dashboard setup completed!")
        print("")
        print("📋 Next steps:")
        print("1. Start the application: streamlit run app.py")
        print("2. Open your browser to: http://localhost:8501")
        print("3. Login with:")
        print("   - Username: admin, Password: admin123 (full access)")
        print("   - Username: hr_user, Password: hr123 (HR domain only)")
        print("   - Username: finance_user, Password: finance123 (Finance domain only)")
        print("   - Username: sales_user, Password: sales123 (Sales domain only)")
        print("")
        print("🔧 Configuration files:")
        print("   - credentials.yaml: User authentication")
        print("   - config.yaml: Dashboard configuration")
        print("")
        print("📊 Features available:")
        print("   - Comprehensive KPI dashboards")
        print("   - Advanced analytics and visualizations")
        print("   - Test management with Airflow integration")
        print("   - Failed records analysis")
        print("   - Multi-format data export")
        print("")
        print("✅ Ready to explore your enhanced data quality dashboard!")
        
    except KeyboardInterrupt:
        print("\n⚠️ Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()