{{ config(
    materialized='table'
) }}

{{ generate_failing_records() }}
