-- models/kpi/table_kpi.sql
{{ config(
    materialized='incremental',
    unique_key=['execution_timestamp', 'schema_name', 'table_name', 'domain'],
    on_schema_change='append_new_columns'
) }}

SELECT
  execution_timestamp,
  domain,
  schema_name,
  table_name,
  AVG(completeness_score) AS avg_completeness_score,
  AVG(uniqueness_score)   AS avg_uniqueness_score,
  AVG(consistency_score) AS avg_consistency_score,
  AVG(validity_score) AS avg_validity_score,
  AVG(accuracy_score) AS avg_accuracy_score,
  AVG(column_score)       AS table_score,
  COUNT(*)                AS num_columns
FROM {{ ref('column_kpi') }}
{% if is_incremental() %}
  -- Only process records that don't exist yet
  WHERE execution_timestamp > (SELECT MAX(execution_timestamp) FROM {{ this }})
{% endif %}
GROUP BY execution_timestamp, schema_name, table_name, domain
ORDER BY execution_timestamp , schema_name, table_name, domain