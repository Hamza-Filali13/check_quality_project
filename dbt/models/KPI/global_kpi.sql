-- models/kpi/global_kpi.sql
{{ config(
    materialized='incremental',
    unique_key=['execution_timestamp', 'database_name', 'domain'],
    on_schema_change='append_new_columns'
) }}

SELECT
  execution_timestamp,
  domain,
  schema_name AS database_name,
  SUM(table_score * num_columns) / NULLIF(SUM(num_columns), 0) AS global_score_weighted_by_columns
FROM {{ ref('table_kpi') }}
{% if is_incremental() %}
  -- Only process records that don't exist yet
  WHERE execution_timestamp > (SELECT MAX(execution_timestamp) FROM {{ this }})
{% endif %}
GROUP BY execution_timestamp, schema_name, domain
ORDER BY execution_timestamp, database_name, domain