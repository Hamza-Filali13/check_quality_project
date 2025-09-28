{{ config(
    materialized='table'
) }}

{% set kpi_tables = var('kpi_tables') %}
{% set test_rows = [] %}

{% for table in kpi_tables %}
    {% set domain = table.get('domain', 'unknown') %}
    {% set schema = table.schema %}
    {% set table_name = table.name %}
    
    {% for column in table.columns %}
        {% set column_name = column.column %}
        {% set checks = column.get('checks', []) %}
        {% set check_count = checks | length %}
        
        {% set row %}
        SELECT 
            '{{ domain }}' as domain,
            '{{ schema }}' as schema_name,
            '{{ table_name }}' as table_name,
            '{{ column_name }}' as column_name,
            '{{ checks | join(",") if checks else "none" }}' as check_types,
            {{ check_count }} as check_count,
            NOW() as created_at
        {% endset %}
        
        {% do test_rows.append(row) %}
    {% endfor %}
{% endfor %}

WITH test_config AS (
    {% if test_rows %}
        {{ test_rows | join('\nUNION ALL\n') }}
    {% else %}
        SELECT 
            'unknown' as domain,
            'unknown' as schema_name, 
            'unknown' as table_name,
            'unknown' as column_name,
            'none' as check_types,
            0 as check_count,
            NOW() as created_at
        WHERE FALSE
    {% endif %}
),

table_summary AS (
    SELECT 
        domain,
        schema_name,
        table_name,
        COUNT(DISTINCT column_name) as column_count,
        SUM(check_count) as total_test_count,
        GROUP_CONCAT(DISTINCT check_types SEPARATOR '|') as all_check_types,
        ROUND(
            100.0 * SUM(CASE WHEN check_count > 0 THEN 1 ELSE 0 END) / COUNT(*), 
            2
        ) as test_coverage_pct,
        MAX(created_at) as created_at
    FROM test_config
    GROUP BY domain, schema_name, table_name
),

domain_summary AS (
    SELECT 
        domain,
        COUNT(DISTINCT CONCAT(schema_name, '.', table_name)) as table_count,
        SUM(column_count) as total_columns,
        SUM(total_test_count) as total_tests,
        ROUND(AVG(total_test_count), 2) as avg_tests_per_table,
        ROUND(AVG(test_coverage_pct), 2) as avg_coverage_pct,
        MAX(created_at) as created_at
    FROM table_summary
    GROUP BY domain
)

SELECT 
    'column' as level, 
    domain, 
    schema_name, 
    table_name, 
    column_name, 
    NULL as table_count, 
    NULL as column_count, 
    check_count as total_tests, 
    check_types as details,
    created_at 
FROM test_config

UNION ALL

SELECT 
    'table' as level, 
    domain, 
    schema_name, 
    table_name, 
    NULL as column_name, 
    NULL as table_count, 
    column_count, 
    total_test_count as total_tests, 
    CONCAT('coverage:', CAST(test_coverage_pct AS CHAR), '%|checks:', COALESCE(all_check_types, 'none')) as details,
    created_at 
FROM table_summary

UNION ALL

SELECT 
    'domain' as level, 
    domain, 
    NULL as schema_name, 
    NULL as table_name, 
    NULL as column_name, 
    table_count, 
    total_columns as column_count, 
    total_tests, 
    CONCAT('avg_tests:', CAST(avg_tests_per_table AS CHAR), '|coverage:', CAST(avg_coverage_pct AS CHAR), '%') as details,
    created_at 
FROM domain_summary