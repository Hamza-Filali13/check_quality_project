from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

# List of your DBT models
dbt_models = [
    "column_kpi",
    "table_kpi",
    "global_kpi",
    "column_kpi_failing",
    "columns_with_issues",
    "failing_records",
    "dq_test_metadata"
]

default_args = {
    "owner": "data-team",
    "depends_on_past": False,
    "start_date": datetime(2025, 9, 17),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    "kpi_dbt_dag",
    description="Run all KPI DBT models",
    default_args=default_args,
    schedule_interval="@daily",
    catchup=False,
    max_active_runs=1,
) as dag:

    previous_task = None

    # Create a BashOperator task for each DBT model
    for model in dbt_models:
        task = BashOperator(
            task_id=f"dbt_run_{model}",
            bash_command=f"""
            cd /opt/airflow/dbt && 
            dbt run --select {model} --profiles-dir /opt/airflow/dbt
            """,
        )

        # Chain tasks sequentially
        if previous_task:
            previous_task >> task

        previous_task = task
