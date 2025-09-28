#!/usr/bin/env python3
"""
Sample Data Generator for Data Quality Dashboard
Generates realistic test results and scores for demonstration purposes
"""

import os
import sys
import psycopg2
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
from typing import List, Dict, Tuple

# Database configuration
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
DB_NAME = os.getenv("POSTGRES_DB", "dq_db")
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "postgres")

# Test configuration
DOMAINS = ["hr", "finance", "sales"]
TABLES = {
    "hr": ["hr.employees"],
    "finance": ["finance.transactions"],
    "sales": ["sales.orders"]
}

COLUMNS = {
    "hr.employees": ["emp_id", "name", "role", "hire_date", "salary", "department", "email"],
    "finance.transactions": ["txn_id", "emp_id", "amount", "txn_date", "description", "status"],
    "sales.orders": ["order_id", "customer_name", "product", "order_date", "quantity", "unit_price", "shipped"]
}

TEST_TYPES = ["completeness", "uniqueness", "validity", "consistency", "accuracy", "timeliness"]

def connect_db():
    """Create database connection"""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )

def generate_test_results(days_back: int = 30, tests_per_day: int = 50) -> List[Dict]:
    """Generate realistic test results"""
    results = []
    
    # Generate data for the last N days
    for day in range(days_back):
        date = datetime.now() - timedelta(days=day)
        
        # Generate tests for this day
        for _ in range(tests_per_day):
            domain = random.choice(DOMAINS)
            table = random.choice(TABLES[domain])
            column = random.choice(COLUMNS[table])
            test_name = random.choice(TEST_TYPES)
            
            # Generate realistic scores based on test type and domain
            base_score = generate_realistic_score(domain, test_name)
            
            # Add some time-based trends
            trend_factor = 1 + (day * 0.002)  # Slight improvement over time
            score = min(100, base_score * trend_factor)
            
            # Determine status based on score
            threshold = get_test_threshold(test_name)
            status = "pass" if score >= threshold else "fail"
            
            result = {
                "table_name": table,
                "column_name": column,
                "test_name": test_name,
                "test_type": "generic",
                "status": status,
                "score": round(score, 2),
                "domain": domain,
                "created_at": date
            }
            
            results.append(result)
    
    return results

def generate_realistic_score(domain: str, test_name: str) -> float:
    """Generate realistic scores based on domain and test type"""
    # Base scores by domain (some domains are naturally better)
    domain_base = {
        "hr": 85,
        "finance": 90,  # Finance typically has better data quality
        "sales": 80
    }
    
    # Test type modifiers
    test_modifiers = {
        "completeness": 0,
        "uniqueness": -5,  # Uniqueness is typically harder
        "validity": 5,
        "consistency": -10,  # Consistency is challenging
        "accuracy": -3,
        "timeliness": 2
    }
    
    base = domain_base.get(domain, 80)
    modifier = test_modifiers.get(test_name, 0)
    
    # Add random variation
    variation = np.random.normal(0, 8)  # Standard deviation of 8
    
    score = base + modifier + variation
    
    # Ensure score is within bounds
    return max(0, min(100, score))

def get_test_threshold(test_name: str) -> float:
    """Get threshold for test type"""
    thresholds = {
        "completeness": 90,
        "uniqueness": 85,
        "validity": 95,
        "consistency": 80,
        "accuracy": 90,
        "timeliness": 75
    }
    
    return thresholds.get(test_name, 85)

def generate_dq_scores(test_results: List[Dict]) -> List[Dict]:
    """Generate DQ scores based on test results"""
    scores = []
    
    # Group by table and date
    df = pd.DataFrame(test_results)
    df['date'] = pd.to_datetime(df['created_at']).dt.date
    
    grouped = df.groupby(['table_name', 'date'])
    
    for (table_name, date), group in grouped:
        # Calculate weighted average score
        weights = {
            "completeness": 0.4,
            "uniqueness": 0.3,
            "validity": 0.2,
            "consistency": 0.05,
            "accuracy": 0.03,
            "timeliness": 0.02
        }
        
        weighted_score = 0
        total_weight = 0
        
        for test_name in group['test_name'].unique():
            test_scores = group[group['test_name'] == test_name]['score']
            if len(test_scores) > 0:
                avg_score = test_scores.mean()
                weight = weights.get(test_name, 0.1)
                weighted_score += avg_score * weight
                total_weight += weight
        
        if total_weight > 0:
            final_score = weighted_score / total_weight
        else:
            final_score = group['score'].mean()
        
        score_record = {
            "table_name": table_name,
            "dq_score": round(final_score, 2),
            "created_at": datetime.combine(date, datetime.min.time())
        }
        
        scores.append(score_record)
    
    return scores

def insert_test_results(results: List[Dict]):
    """Insert test results into database"""
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        # Create table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dbt.dq_test_results (
                id SERIAL PRIMARY KEY,
                table_name TEXT,
                column_name TEXT,
                test_name TEXT,
                test_type TEXT,
                status TEXT,
                score NUMERIC,
                domain TEXT,
                created_at TIMESTAMP
            )
        """)
        
        # Clear existing data
        cursor.execute("DELETE FROM dbt.dq_test_results")
        
        # Insert new data
        insert_query = """
            INSERT INTO dbt.dq_test_results 
            (table_name, column_name, test_name, test_type, status, score, domain, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        for result in results:
            cursor.execute(insert_query, (
                result["table_name"],
                result["column_name"],
                result["test_name"],
                result["test_type"],
                result["status"],
                result["score"],
                result["domain"],
                result["created_at"]
            ))
        
        conn.commit()
        print(f"✅ Inserted {len(results)} test results")
        
    except Exception as e:
        print(f"❌ Error inserting test results: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def insert_dq_scores(scores: List[Dict]):
    """Insert DQ scores into database"""
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        # Create table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dbt.dq_score (
                id SERIAL PRIMARY KEY,
                table_name TEXT,
                dq_score NUMERIC,
                created_at TIMESTAMP
            )
        """)
        
        # Clear existing data
        cursor.execute("DELETE FROM dbt.dq_score")
        
        # Insert new data
        insert_query = """
            INSERT INTO dbt.dq_score (table_name, dq_score, created_at)
            VALUES (%s, %s, %s)
        """
        
        for score in scores:
            cursor.execute(insert_query, (
                score["table_name"],
                score["dq_score"],
                score["created_at"]
            ))
        
        conn.commit()
        print(f"✅ Inserted {len(scores)} DQ scores")
        
    except Exception as e:
        print(f"❌ Error inserting DQ scores: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def create_schemas():
    """Create necessary database schemas"""
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("CREATE SCHEMA IF NOT EXISTS dbt")
        conn.commit()
        print("✅ Created dbt schema")
    except Exception as e:
        print(f"❌ Error creating schema: {e}")
    finally:
        cursor.close()
        conn.close()

def generate_sample_issues():
    """Generate some sample data quality issues for demonstration"""
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        # Create issues table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dbt.dq_issues (
                id SERIAL PRIMARY KEY,
                table_name TEXT,
                column_name TEXT,
                issue_type TEXT,
                description TEXT,
                severity TEXT,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP
            )
        """)
        
        # Sample issues
        issues = [
            {
                "table_name": "hr.employees",
                "column_name": "email",
                "issue_type": "completeness",
                "description": "Missing email addresses for 15% of employees",
                "severity": "Medium",
                "status": "Open"
            },
            {
                "table_name": "finance.transactions",
                "column_name": "amount",
                "issue_type": "validity",
                "description": "Negative transaction amounts detected",
                "severity": "High",
                "status": "Open"
            },
            {
                "table_name": "sales.orders",
                "column_name": "product",
                "issue_type": "completeness",
                "description": "Product name missing for recent orders",
                "severity": "Critical",
                "status": "In Progress"
            }
        ]
        
        # Clear existing issues
        cursor.execute("DELETE FROM dbt.dq_issues")
        
        # Insert sample issues
        for issue in issues:
            cursor.execute("""
                INSERT INTO dbt.dq_issues 
                (table_name, column_name, issue_type, description, severity, status)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                issue["table_name"],
                issue["column_name"],
                issue["issue_type"],
                issue["description"],
                issue["severity"],
                issue["status"]
            ))
        
        conn.commit()
        print(f"✅ Created {len(issues)} sample issues")
        
    except Exception as e:
        print(f"❌ Error creating sample issues: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def main():
    """Main function to generate all sample data"""
    print("🚀 Starting sample data generation...")
    
    try:
        # Create schemas
        create_schemas()
        
        # Generate test results
        print("📊 Generating test results...")
        test_results = generate_test_results(days_back=30, tests_per_day=50)
        insert_test_results(test_results)
        
        # Generate DQ scores
        print("📈 Generating DQ scores...")
        dq_scores = generate_dq_scores(test_results)
        insert_dq_scores(dq_scores)
        
        # Generate sample issues
        print("🔍 Generating sample issues...")
        generate_sample_issues()
        
        print("✅ Sample data generation completed successfully!")
        print(f"📊 Generated {len(test_results)} test results")
        print(f"📈 Generated {len(dq_scores)} DQ scores")
        print("🎉 Ready to explore the enhanced dashboard!")
        
    except Exception as e:
        print(f"❌ Error during data generation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()