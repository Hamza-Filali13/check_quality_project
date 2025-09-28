-- models/kpi/column_kpi.sql
-- Configure as incremental model
{{ config(
    materialized='incremental',
    unique_key=['execution_timestamp', 'schema_name', 'table_name', 'column_name', 'domain'],
    on_schema_change='append_new_columns'
) }}

{{ generate_table_kpis() }}

-- Only load new data on incremental runs
{% if is_incremental() %}
  -- This filter will be applied on an incremental run
  -- You might want to adjust this logic based on your needs
{% endif %}