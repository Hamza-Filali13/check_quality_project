#!/usr/bin/env python3
"""
Complete setup script for the enhanced DQ Streamlit App
This script sets up the database, runs dbt models, and starts the app
"""

import subprocess
import sys
import os
import time
import psycopg2
from pathlib import Path

def run_command(command, description, cwd=None):
    """Run a command and handle errors"""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            check=True, 
            capture_output=True, 
            text=True,
            cwd=cwd
        )
        print(f"✅ {description} completed successfully")
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"Error: {e.stderr}")
        return None

def check_database_connection():
    """Check if database is accessible"""
    try:
        conn = psycopg2.connect(
            host="localhost",
            port="5432",
            database="dq_db",
            user="dq_user",
            password="dq_password"
        )
        conn.close()
        print("✅ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def setup_database():
    """Set up database with enhanced sample data"""
    print("\n📊 Setting up database with enhanced sample data...")
    
    if not check_database_connection():
        print("Please ensure PostgreSQL is running and accessible")
        return False
    
    # Run the enhanced sample data script
    if os.path.exists("populate_enhanced_sample_data.sql"):
        run_command(
            'psql -h localhost -p 5432 -U dq_user -d dq_db -f populate_enhanced_sample_data.sql',
            "Loading enhanced sample data"
        )
    
    return True

def setup_dbt():
    """Set up and run dbt models"""
    print("\n🔧 Setting up dbt models...")
    
    dbt_dir = Path("dbt/dq_dbt_project")
    if not dbt_dir.exists():
        print(f"❌ dbt directory not found: {dbt_dir}")
        return False
    
    # Install dbt dependencies
    run_command("dbt deps", "Installing dbt dependencies", cwd=dbt_dir)
    
    # Run dbt models
    run_command("dbt run", "Running dbt models", cwd=dbt_dir)
    
    # Run dbt tests
    run_command("dbt test", "Running dbt tests", cwd=dbt_dir)
    
    return True

def install_requirements():
    """Install Python requirements"""
    print("\n📦 Installing Python requirements...")
    
    streamlit_dir = Path("streamlit_app")
    requirements_file = streamlit_dir / "requirements.txt"
    
    if requirements_file.exists():
        run_command(
            f"pip install -r {requirements_file}",
            "Installing Python packages"
        )
    else:
        print(f"❌ Requirements file not found: {requirements_file}")
        return False
    
    return True

def test_app_components():
    """Test app components"""
    print("\n🧪 Testing app components...")
    
    streamlit_dir = Path("streamlit_app")
    test_script = streamlit_dir / "test_db_connection.py"
    
    if test_script.exists():
        run_command(
            f"python {test_script}",
            "Testing database connection",
            cwd=streamlit_dir
        )
    
    return True

def start_streamlit_app():
    """Start the Streamlit app"""
    print("\n🚀 Starting Streamlit app...")
    
    streamlit_dir = Path("streamlit_app")
    app_file = streamlit_dir / "app.py"
    
    if not app_file.exists():
        print(f"❌ App file not found: {app_file}")
        return False
    
    print("🌐 Starting Streamlit server...")
    print("📱 App will be available at: http://localhost:8501")
    print("🔑 Demo login credentials:")
    print("   Admin: admin / admin")
    print("   HR User: hr_user / password")
    print("   Finance User: finance_user / password")
    print("   Sales User: sales_user / password")
    print("\n🛑 Press Ctrl+C to stop the app")
    print("-" * 60)
    
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", str(app_file),
            "--server.port", "8501",
            "--server.address", "0.0.0.0",
            "--browser.gatherUsageStats", "false"
        ], cwd=streamlit_dir)
    except KeyboardInterrupt:
        print("\n👋 App stopped by user")
    except Exception as e:
        print(f"❌ Error running app: {e}")

def main():
    """Main setup function"""
    print("🎯 DXC Data Quality Platform - Complete Setup")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("streamlit_app").exists() or not Path("dbt").exists():
        print("❌ Please run this script from the project root directory")
        print("   Expected structure:")
        print("   - streamlit_app/")
        print("   - dbt/")
        print("   - docker-compose.yml")
        return
    
    # Setup steps
    steps = [
        ("📦 Install Requirements", install_requirements),
        ("📊 Setup Database", setup_database),
        ("🔧 Setup dbt", setup_dbt),
        ("🧪 Test Components", test_app_components),
    ]
    
    for step_name, step_func in steps:
        print(f"\n{step_name}")
        print("-" * 30)
        if not step_func():
            print(f"❌ {step_name} failed. Please check the errors above.")
            response = input("Do you want to continue anyway? (y/n): ")
            if response.lower() != 'y':
                return
    
    print("\n✅ Setup completed successfully!")
    print("\nWhat's been set up:")
    print("- ✅ Enhanced database with comprehensive test data")
    print("- ✅ Advanced dbt models with multiple data quality tests")
    print("- ✅ Modern Streamlit app with AG-Grid tables")
    print("- ✅ Interactive Plotly visualizations")
    print("- ✅ Domain-based access control")
    print("- ✅ Drill-down to failed records")
    print("- ✅ Professional login interface")
    
    # Ask if user wants to start the app
    response = input("\n🚀 Do you want to start the Streamlit app now? (y/n): ")
    if response.lower() == 'y':
        start_streamlit_app()
    else:
        print("\n📝 To start the app later, run:")
        print("   cd streamlit_app")
        print("   python run_app.py")
        print("   or")
        print("   streamlit run app.py")

if __name__ == "__main__":
    main()
