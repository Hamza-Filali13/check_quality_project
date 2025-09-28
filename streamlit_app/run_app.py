#!/usr/bin/env python3
"""
Startup script for the Data Quality Streamlit App
"""

import subprocess
import sys
import os

def main():
    """Run the Streamlit app"""
    print("🚀 Starting Data Quality Dashboard...")
    print("📊 App will be available at: http://localhost:8501")
    print("🔧 Press Ctrl+C to stop the app")
    print("-" * 50)
    
    # Change to the streamlit_app directory
    app_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(app_dir)
    
    try:
        # Run streamlit
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "app.py",
            "--server.port", "8501",
            "--server.address", "0.0.0.0",
            "--browser.gatherUsageStats", "false"
        ])
    except KeyboardInterrupt:
        print("\n👋 App stopped by user")
    except Exception as e:
        print(f"❌ Error running app: {e}")

if __name__ == "__main__":
    main()
