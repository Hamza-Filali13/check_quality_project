{% macro generate_table_kpis() %}
    {% set statements = [] %}

    {% for table in var('kpi_tables') %}
        {% for col in table.columns %}
            {% set stmt = column_metrics(table.schema, table.name, col.column, col, table.get('domain', 'unknown')) %}
            {% do statements.append(stmt) %}
        {% endfor %}
    {% endfor %}

    {{ return(statements | join(" UNION ALL ")) }}
{% endmacro %}