#!/bin/sh
set -e

# Add local pip binaries to PATH
export PATH=/home/airflow/.local/bin:$PATH

echo "=== Installing DBT and dependencies ==="
# Only install DBT if not already installed
pip show dbt-core >/dev/null 2>&1 || \
pip install --no-cache-dir "protobuf<6.0.0" dbt-core==1.7.9 dbt-mysql==1.7.0 mysqlclient

echo "=== Initializing Airflow DB ==="
# Init or upgrade Airflow metadata DB
airflow db init || true
airflow db upgrade

echo "=== Creating default admin user if missing ==="
airflow users create \
  --username admin \
  --password admin \
  --firstname Admin \
  --lastname User \
  --role Admin \
  --email admin@example.com || true

echo "=== Starting Airflow scheduler in background ==="
airflow scheduler &

echo "=== Starting Airflow webserver in foreground ==="
exec airflow webserver
