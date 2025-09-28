{% macro generate_failing_records() %}
    {%- set kpi_tables = var('kpi_tables') -%}
    {%- set checks = [] -%}

    {% for table in kpi_tables %}
        {%- set domain = table.get('domain', 'unknown') -%}  {# Get domain or default to 'unknown' #}
        {%- set all_cols = adapter.get_columns_in_relation(source(table.schema, table.name)) -%}
        {%- set col_names = all_cols | map(attribute='name') | list -%}
        
        {% for column in table.columns %}
            {% set col_name = column.column %}

            {# Null Check #}
            {% if 'null' in column.checks %}
                {% set description = column.get("null_description", "Null check failed") %}
                {% set description_safe = description | replace("'", "''") | replace("%", "%%") %}
                {% set check_query %}
                    select '{{ domain }}' as domain,  -- Added domain field
                           '{{ table.name }}' as table_name,
                           '{{ col_name }}' as column_name,
                           'Completeness' as dimension,
                           'null' as check_type,
                           '{{ description_safe }}' as test_description,
                           case when t.{{ col_name }} is null then 'NULL' else cast(t.{{ col_name }} as char) end as column_value,
                           concat_ws(' | ', {% for c in col_names %}case when t.`{{ c }}` is null then 'NULL' else cast(t.`{{ c }}` as char) end{% if not loop.last %}, {% endif %}{% endfor %}) as record
                    from {{ source(table.schema, table.name) }} t
                    where t.{{ col_name }} is null
                {% endset %}
                {% do checks.append(check_query) %}
            {% endif %}

            {# Threshold Check #}
            {% if 'threshold' in column.checks %}
                {% set threshold = column.get("threshold") %}
                {% set description = column.get("threshold_description", "Threshold check failed") %}
                {% set description_safe = description | replace("'", "''") | replace("%", "%%") %}
                {% set check_query %}
                    select '{{ domain }}' as domain,  -- Added domain field
                           '{{ table.name }}' as table_name,
                           '{{ col_name }}' as column_name,
                           'Completeness' as dimension,
                           'threshold' as check_type,
                           '{{ description_safe }}' as test_description,
                           cast(t.{{ col_name }} as char) as column_value,
                           concat_ws(' | ', {% for c in col_names %}cast(t.`{{ c }}` as char){% if not loop.last %}, {% endif %}{% endfor %}) as record
                    from {{ source(table.schema, table.name) }} t
                    join (
                        select 1 as dummy
                        from {{ source(table.schema, table.name) }}
                        having sum(case when {{ col_name }} is null then 1 else 0 end) * 100.0 / nullif(count(*), 0) > {{ threshold }}
                    ) stats on 1=1
                    where t.{{ col_name }} is null
                {% endset %}
                {% do checks.append(check_query) %}
            {% endif %}

            {# Foreign Key Check #}
            {% if 'foreign_key' in column.checks %}
                {% set foreign_table = column.get("foreign_table") %}
                {% set foreign_column = column.get("foreign_column") %}
                {% set description = column.get("foreign_key_description", "Foreign key check failed") %}
                {% set description_safe = description | replace("'", "''") | replace("%", "%%") %}
                {% set check_query %}
                    select '{{ domain }}' as domain,  -- Added domain field
                           '{{ table.name }}' as table_name,
                           '{{ col_name }}' as column_name,
                           'Validity' as dimension,
                           'foreign_key' as check_type,
                           '{{ description_safe }}' as test_description,
                           cast(t.{{ col_name }} as char) as column_value,
                           concat_ws(' | ', {% for c in col_names %}cast(t.`{{ c }}` as char){% if not loop.last %}, {% endif %}{% endfor %}) as record
                    from {{ source(table.schema, table.name) }} t
                    left join {{ source(column.get("foreign_schema", table.schema), foreign_table) }} f
                        on t.{{ col_name }} = f.{{ foreign_column }}
                    where t.{{ col_name }} is not null and f.{{ foreign_column }} is null
                {% endset %}
                {% do checks.append(check_query) %}
            {% endif %}

            {# Uniqueness Check #}
            {% if 'uniqueness' in column.checks %}
                {% set description = column.get("uniqueness_description", "Uniqueness check failed") %}
                {% set description_safe = description | replace("'", "''") | replace("%", "%%") %}
                {% set check_query %}
                    select '{{ domain }}' as domain,  -- Added domain field
                           '{{ table.name }}' as table_name,
                           '{{ col_name }}' as column_name,
                           'Uniqueness' as dimension,
                           'uniqueness' as check_type,
                           '{{ description_safe }}' as test_description,
                           cast(t.{{ col_name }} as char) as column_value,
                           concat_ws(' | ', {% for c in col_names %}cast(t.`{{ c }}` as char){% if not loop.last %}, {% endif %}{% endfor %}) as record
                    from {{ source(table.schema, table.name) }} t
                    join (
                        select {{ col_name }}
                        from {{ source(table.schema, table.name) }}
                        where {{ col_name }} is not null
                        group by {{ col_name }}
                        having count(*) > 1
                    ) duplicates on t.{{ col_name }} = duplicates.{{ col_name }}
                {% endset %}
                {% do checks.append(check_query) %}
            {% endif %}

            {# Consistency Check #}
            {% if 'consistency' in column.checks %}
                {% set rule = column.get("consistency_rule") %}
                {% set description = column.get("consistency_description", "Consistency check failed") %}
                {% set description_safe = description | replace("'", "''") | replace("%", "%%") %}
                {% set check_query %}
                    select '{{ domain }}' as domain,  -- Added domain field
                           '{{ table.name }}' as table_name,
                           '{{ col_name }}' as column_name,
                           'Consistency' as dimension,
                           'consistency' as check_type,
                           '{{ description_safe }}' as test_description,
                           cast(t.{{ col_name }} as char) as column_value,
                           concat_ws(' | ', {% for c in col_names %}cast(t.`{{ c }}` as char){% if not loop.last %}, {% endif %}{% endfor %}) as record
                    from {{ source(table.schema, table.name) }} t
                    where not ({{ rule }})
                {% endset %}
                {% do checks.append(check_query) %}
            {% endif %}

            {# Validity Check #}
            {% if 'validity' in column.checks %}
                {% set rule = column.get("validity_rule") %}
                {% set description = column.get("validity_description", "Validity check failed") %}
                {% set description_safe = description | replace("'", "''") | replace("%", "%%") %}
                {% set check_query %}
                    select '{{ domain }}' as domain,  -- Added domain field
                           '{{ table.name }}' as table_name,
                           '{{ col_name }}' as column_name,
                           'Validity' as dimension,
                           'validity' as check_type,
                           '{{ description_safe }}' as test_description,
                           cast(t.{{ col_name }} as char) as column_value,
                           concat_ws(' | ', {% for c in col_names %}cast(t.`{{ c }}` as char){% if not loop.last %}, {% endif %}{% endfor %}) as record
                    from {{ source(table.schema, table.name) }} t
                    where t.{{ col_name }} is not null and not ({{ rule }})
                {% endset %}
                {% do checks.append(check_query) %}
            {% endif %}

            {# Regex Check #}
            {% if 'regex' in column.checks %}
                {% set pattern = column.get("regex_pattern") %}
                {% set description = column.get("regex_description", "Regex check failed") %}
                {% set description_safe = description | replace("'", "''") | replace("%", "%%") %}
                {% set check_query %}
                    select '{{ domain }}' as domain,  -- Added domain field
                           '{{ table.name }}' as table_name,
                           '{{ col_name }}' as column_name,
                           'Validity' as dimension,
                           'regex' as check_type,
                           '{{ description_safe }}' as test_description,
                           cast(t.{{ col_name }} as char) as column_value,
                           concat_ws(' | ', {% for c in col_names %}cast(t.`{{ c }}` as char){% if not loop.last %}, {% endif %}{% endfor %}) as record
                    from {{ source(table.schema, table.name) }} t
                    where t.{{ col_name }} is not null and t.{{ col_name }} not regexp '{{ pattern }}'
                {% endset %}
                {% do checks.append(check_query) %}
            {% endif %}

            {# Domain Check #}
            {% if 'domain' in column.checks %}
                {% set values = column.get("domain_values") %}
                {% if values is not none and values | length > 0 %}
                    {% set quoted_values = [] %}
                    {% for val in values %}
                        {% if val is string %}
                            {% do quoted_values.append("'" ~ val | replace("'", "''") ~ "'") %}
                        {% else %}
                            {% do quoted_values.append(val | string) %}
                        {% endif %}
                    {% endfor %}
                    {% set values_str = quoted_values | join(", ") %}
                    {% set description = column.get("domain_description", "Domain check failed") %}
                    {% set description_safe = description | replace("'", "''") | replace("%", "%%") %}
                    {% set check_query %}
                        select '{{ domain }}' as domain,  -- Added domain field
                               '{{ table.name }}' as table_name,
                               '{{ col_name }}' as column_name,
                               'Validity' as dimension,
                               'domain' as check_type,
                               '{{ description_safe }}' as test_description,
                               cast(t.{{ col_name }} as char) as column_value,
                               concat_ws(' | ', {% for c in col_names %}cast(t.`{{ c }}` as char){% if not loop.last %}, {% endif %}{% endfor %}) as record
                        from {{ source(table.schema, table.name) }} t
                        where t.{{ col_name }} is not null and t.{{ col_name }} not in ({{ values_str }})
                    {% endset %}
                    {% do checks.append(check_query) %}
                {% endif %}
            {% endif %}

            {# Accuracy: Rule #}
            {% if 'accuracy' in column.checks and column.get("accuracy_rule") %}
                {% set rule = column.get("accuracy_rule") %}
                {% set description = column.get("accuracy_description", "Accuracy check failed") %}
                {% set description_safe = description | replace("'", "''") | replace("%", "%%") %}
                {% set check_query %}
                    select '{{ domain }}' as domain,  -- Added domain field
                           '{{ table.name }}' as table_name,
                           '{{ col_name }}' as column_name,
                           'Accuracy' as dimension,
                           'accuracy' as check_type,
                           '{{ description_safe }}' as test_description,
                           cast(t.{{ col_name }} as char) as column_value,
                           concat_ws(' | ', {% for c in col_names %}cast(t.`{{ c }}` as char){% if not loop.last %}, {% endif %}{% endfor %}) as record
                    from {{ source(table.schema, table.name) }} t
                    where t.{{ col_name }} is not null and not ({{ rule }})
                {% endset %}
                {% do checks.append(check_query) %}
            {% endif %}

            {# Accuracy: Reference Match #}
            {% if 'accuracy' in column.checks and column.get("accuracy_table") %}
                {% set acc_table = column.get("accuracy_table") %}
                {% set acc_column = column.get("accuracy_column") %}
                {% set description = column.get("accuracy_description", "Accuracy check failed") %}
                {% set description_safe = description | replace("'", "''") | replace("%", "%%") %}
                {% set check_query %}
                    select '{{ domain }}' as domain,  -- Added domain field
                           '{{ table.name }}' as table_name,
                           '{{ col_name }}' as column_name,
                           'Accuracy' as dimension,
                           'accuracy' as check_type,
                           '{{ description_safe }}' as test_description,
                           cast(t.{{ col_name }} as char) as column_value,
                           concat_ws(' | ', {% for c in col_names %}cast(t.`{{ c }}` as char){% if not loop.last %}, {% endif %}{% endfor %}) as record
                    from {{ source(table.schema, table.name) }} t
                    left join {{ source(column.get("accuracy_schema", table.schema), acc_table) }} a
                        on t.{{ col_name }} = a.{{ acc_column }}
                    where t.{{ col_name }} is not null and a.{{ acc_column }} is null
                {% endset %}
                {% do checks.append(check_query) %}
            {% endif %}

        {% endfor %}
    {% endfor %}

    {% if checks | length > 0 %}
        {{ checks | join("\nunion all\n") }}
    {% else %}
        select 'unknown' as domain,  -- Added domain field for fallback
               'No tables configured' as table_name,
               'N/A' as column_name,
               'Info' as dimension,
               'info' as check_type,
               'No quality checks configured' as test_description,
               'N/A' as column_value,
               'N/A' as record
        where false
    {% endif %}
{% endmacro %}