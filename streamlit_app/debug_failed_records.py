#!/usr/bin/env python3
"""
Debug script to check failed records format and query them back
Run this from the streamlit_app directory
"""

from services.db import run_query, run_query_with_params
import pandas as pd
import json

def check_database_structure():
    """Check what tables exist and their structure"""
    print("=== DATABASE STRUCTURE ===")
    
    # Check available tables
    tables_query = """
    SELECT table_schema, table_name 
    FROM information_schema.tables 
    WHERE table_schema IN ('dbt', 'hr', 'finance', 'sales')
    ORDER BY table_schema, table_name
    """
    tables_df = run_query(tables_query)
    print("\nAvailable Tables:")
    print(tables_df.to_string(index=False))
    
    # Check dq_test_results structure and sample data
    print("\n=== DQ_TEST_RESULTS SAMPLE ===")
    try:
        test_results_query = """
        SELECT domain, table_name, test_name, column_name, status, COUNT(*) as count
        FROM dbt.dq_test_results 
        GROUP BY domain, table_name, test_name, column_name, status
        ORDER BY domain, table_name, test_name
        LIMIT 10
        """
        test_results_df = run_query(test_results_query)
        print(test_results_df.to_string(index=False))
    except Exception as e:
        print(f"Error querying dq_test_results: {e}")
    
    # Check if dq_record_failures exists
    print("\n=== DQ_RECORD_FAILURES CHECK ===")
    try:
        count_query = "SELECT COUNT(*) as count FROM dbt.dq_record_failures"
        count_df = run_query(count_query)
        record_count = count_df.iloc[0]['count']
        print(f"Records in dq_record_failures: {record_count}")
        
        if record_count > 0:
            sample_query = "SELECT * FROM dbt.dq_record_failures LIMIT 3"
            sample_df = run_query(sample_query)
            print("\nSample failed records:")
            for idx, row in sample_df.iterrows():
                print(f"\nRecord {idx + 1}:")
                print(f"  failure_id: {row.get('failure_id')}")
                print(f"  result_id: {row.get('result_id')}")
                print(f"  table_name: {row.get('table_name')}")
                print(f"  domain: {row.get('domain')}")
                print(f"  record_identifier: {row.get('record_identifier')}")
                if row.get('record_data'):
                    try:
                        record_data = json.loads(row['record_data'])
                        print(f"  record_data: {record_data}")
                    except:
                        print(f"  record_data: {row.get('record_data')}")
                        
    except Exception as e:
        print(f"dq_record_failures table doesn't exist or error: {e}")

def test_failed_record_query(domain, table_name, test_name, column_name):
    """Test querying for a specific failed test"""
    print(f"\n=== TESTING QUERY FOR: {domain}.{table_name} - {test_name} - {column_name} ===")
    
    # Step 1: Query dq_test_results
    result_query = """
    SELECT result_id, status, records_failed, execution_timestamp
    FROM dbt.dq_test_results
    WHERE domain = %s 
        AND table_name = %s 
        AND test_name = %s 
        AND column_name = %s
    ORDER BY execution_timestamp DESC
    LIMIT 5
    """
    
    try:
        result_df = run_query_with_params(result_query, (domain, table_name, test_name, column_name))
        print(f"\nFound {len(result_df)} test results:")
        print(result_df.to_string(index=False))
        
        if not result_df.empty:
            result_id = result_df.iloc[0]['result_id']
            print(f"\nUsing result_id: {result_id}")
            
            # Step 2: Try to get from dq_record_failures
            try:
                failed_records_query = """
                SELECT failure_id, record_identifier, record_data, failure_reason
                FROM dbt.dq_record_failures
                WHERE result_id = %s
                LIMIT 5
                """
                
                records_df = run_query_with_params(failed_records_query, (result_id,))
                print(f"\nFound {len(records_df)} failed records in dq_record_failures:")
                
                for idx, row in records_df.iterrows():
                    print(f"\nFailed Record {idx + 1}:")
                    print(f"  failure_id: {row['failure_id']}")
                    print(f"  record_identifier: {row['record_identifier']}")
                    print(f"  failure_reason: {row['failure_reason']}")
                    if row['record_data']:
                        try:
                            record_data = json.loads(row['record_data'])
                            print(f"  record_data: {record_data}")
                        except:
                            print(f"  record_data (raw): {row['record_data']}")
                            
            except Exception as e:
                print(f"Error querying dq_record_failures: {e}")
                
    except Exception as e:
        print(f"Error querying dq_test_results: {e}")

def test_source_table_query(domain, table_name, column_name, test_type):
    """Test querying source table directly"""
    print(f"\n=== TESTING DIRECT SOURCE QUERY: {domain}.{table_name} ===")
    
    table_configs = {
        'hr.employees': ['emp_id', 'name', 'email', 'department', 'salary', 'hire_date', 'role'],
        'finance.transactions': ['txn_id', 'emp_id', 'amount', 'txn_date', 'description', 'status'],
        'sales.orders': ['order_id', 'customer_name', 'product', 'order_date', 'quantity', 'unit_price', 'shipped']
    }
    
    full_table_name = f"{domain}.{table_name}"
    if full_table_name not in table_configs:
        print(f"No configuration for {full_table_name}")
        return
        
    columns = table_configs[full_table_name]
    
    if test_type == 'completeness':
        source_query = f"""
        SELECT {', '.join(columns)}
        FROM {domain}.{table_name}
        WHERE {column_name} IS NULL OR TRIM(CAST({column_name} AS TEXT)) = ''
        LIMIT 5
        """
    elif test_type == 'uniqueness':
        source_query = f"""
        SELECT {', '.join(columns)}
        FROM {domain}.{table_name}
        WHERE {column_name} IN (
            SELECT {column_name}
            FROM {domain}.{table_name}
            WHERE {column_name} IS NOT NULL
            GROUP BY {column_name} 
            HAVING COUNT(*) > 1
        )
        LIMIT 5
        """
    elif test_type == 'validity_email':
        source_query = f"""
        SELECT {', '.join(columns)}
        FROM {domain}.{table_name}
        WHERE {column_name} IS NOT NULL 
        AND NOT {column_name} ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'
        LIMIT 5
        """
    else:
        print(f"Unknown test type: {test_type}")
        return
    
    print(f"\nExecuting query:")
    print(source_query)
    
    try:
        source_df = run_query(source_query)
        print(f"\nFound {len(source_df)} records:")
        if not source_df.empty:
            print(source_df.to_string(index=False))
        else:
            print("No records found (all data passes this test)")
    except Exception as e:
        print(f"Error executing source query: {e}")

if __name__ == "__main__":
    print("🔍 FAILED RECORDS DEBUG TOOL")
    print("=" * 50)
    
    # Check database structure
    check_database_structure()
    
    # Test some common queries
    print("\n" + "=" * 50)
    print("🧪 TESTING COMMON QUERIES")
    
    # Test HR completeness
    test_failed_record_query('hr', 'hr.employees', 'completeness_not_null_name', 'name')
    test_source_table_query('hr', 'employees', 'name', 'completeness')
    
    # Test HR email validity  
    test_failed_record_query('hr', 'hr.employees', 'validity_email_format_email', 'email')
    test_source_table_query('hr', 'employees', 'email', 'validity_email')
    
    # Test Finance completeness
    test_failed_record_query('finance', 'finance.transactions', 'completeness_not_null_txn_id', 'txn_id')
    test_source_table_query('finance', 'transactions', 'txn_id', 'completeness')
    
    print("\n" + "=" * 50)
    print("✅ Debug complete!")
