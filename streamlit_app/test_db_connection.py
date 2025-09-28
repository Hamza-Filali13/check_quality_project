#!/usr/bin/env python3
"""
Test script to verify database connection and dbt table access
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.db import run_query
import pandas as pd

def test_connection():
    """Test database connection and dbt tables"""
    print("🔍 Testing database connection...")
    
    try:
        # Test basic connection
        result = run_query("SELECT 1 as test")
        print("✅ Database connection successful")
        
        # Test dbt tables
        print("\n📊 Testing dbt tables...")
        
        # Check dq_score table
        try:
            dq_score = run_query("SELECT COUNT(*) as count FROM dbt.dq_score")
            print(f"✅ dbt.dq_score table accessible - {dq_score.iloc[0]['count']} records")
        except Exception as e:
            print(f"❌ dbt.dq_score table error: {e}")
        
        # Check dq_test_results table
        try:
            dq_test = run_query("SELECT COUNT(*) as count FROM dbt.dq_test_results")
            print(f"✅ dbt.dq_test_results table accessible - {dq_test.iloc[0]['count']} records")
        except Exception as e:
            print(f"❌ dbt.dq_test_results table error: {e}")
        
        # Check dq_metrics_model table
        try:
            dq_metrics = run_query("SELECT COUNT(*) as count FROM dbt.dq_metrics_model")
            print(f"✅ dbt.dq_metrics_model table accessible - {dq_metrics.iloc[0]['count']} records")
        except Exception as e:
            print(f"❌ dbt.dq_metrics_model table error: {e}")
        
        # Show sample data
        print("\n📋 Sample data from dq_score:")
        try:
            sample = run_query("SELECT * FROM dbt.dq_score LIMIT 5")
            print(sample.to_string())
        except Exception as e:
            print(f"❌ Error getting sample data: {e}")
            
        print("\n📋 Sample data from dq_test_results:")
        try:
            sample = run_query("SELECT * FROM dbt.dq_test_results LIMIT 5")
            print(sample.to_string())
        except Exception as e:
            print(f"❌ Error getting sample data: {e}")
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    test_connection()
