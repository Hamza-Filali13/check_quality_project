-- Updated column_metrics macro
{% macro column_metrics(schema, table, column, column_config=None, domain='unknown') %} 
SELECT 
    CURRENT_TIMESTAMP AS execution_timestamp,  -- Added execution timestamp
    '{{ domain }}' AS domain,
    '{{ schema }}' AS schema_name, 
    '{{ table }}' AS table_name, 
    '{{ column }}' AS column_name, 
 
    -- Completeness
    {% if column_config and ('null' in column_config.get('checks', []) or 'threshold' in column_config.get('checks', [])) %}
        (
            (COUNT(*) - SUM(CASE WHEN {{ column }} IS NULL THEN 1 ELSE 0 END)) * 100.0 / NULLIF(COUNT(*), 0)
        ) AS completeness_score,
    {% else %}
        NULL AS completeness_score,
    {% endif %}
 
    -- Uniqueness
    {% if column_config and 'uniqueness' in column_config.get('checks', []) %}
        (COUNT(DISTINCT {{ column }}) * 100.0 / NULLIF(COUNT(*), 0)) AS uniqueness_score,
    {% else %}
        NULL AS uniqueness_score,
    {% endif %}
 
    -- Consistency 
    {% if column_config and 'consistency' in column_config.get('checks', []) and column_config.get('consistency_rule') %} 
        (SUM(CASE WHEN {{ column_config['consistency_rule'] }} THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0)) AS consistency_score, 
    {% else %} 
        NULL AS consistency_score, 
    {% endif %} 
 
    -- Validity 
    {% set validity_checks = [] %} 
    {% if column_config and column_config.get('checks', []) %}
        {% if 'regex' in column_config.checks and column_config.get('regex_pattern') %} 
            {% do validity_checks.append("(CASE WHEN " ~ column ~ " IS NOT NULL AND " ~ column ~ " NOT REGEXP '" ~ column_config['regex_pattern'] ~ "' THEN 0 ELSE 1 END)") %} 
        {% endif %} 
        {% if 'domain' in column_config.checks and column_config.get('domain_values') %} 
            {% set domain_vals = [] %} 
            {% for val in column_config['domain_values'] %} 
                {% do domain_vals.append("'" ~ val ~ "'") %} 
            {% endfor %} 
            {% do validity_checks.append("(CASE WHEN " ~ column ~ " IN (" ~ domain_vals | join(',') ~ ") THEN 1 ELSE 0 END)") %} 
        {% endif %} 
        {% if 'validity' in column_config.checks and column_config.get('validity_rule') %} 
            {% do validity_checks.append("(CASE WHEN " ~ column_config['validity_rule'] ~ " THEN 1 ELSE 0 END)") %} 
        {% endif %} 
    {% endif %} 
 
    {% if validity_checks | length > 0 %} 
        (SUM({{ validity_checks | join(' + ') }}) * 100.0 / (NULLIF(COUNT(*),0) * {{ validity_checks | length }})) AS validity_score, 
    {% else %} 
        NULL AS validity_score, 
    {% endif %} 
 
    -- Accuracy 
    {% if column_config and 'accuracy' in column_config.get('checks', []) and column_config.get('accuracy_rule') %} 
        (SUM(CASE WHEN {{ column_config['accuracy_rule'] }} THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0)) AS accuracy_score, 
    {% else %} 
        NULL AS accuracy_score, 
    {% endif %} 
 
    -- Overall score (only include dimensions that are being tested)
    {% set score_components = [] %}
    {% set total_dimensions = 0 %}
    
    {% if column_config and column_config.get('checks', []) %}
        {% if 'null' in column_config.checks %}
            {% do score_components.append("COALESCE(((COUNT(*) - SUM(CASE WHEN " ~ column ~ " IS NULL THEN 1 ELSE 0 END)) * 100.0 / NULLIF(COUNT(*), 0)), 0)") %}
            {% set total_dimensions = total_dimensions + 1 %}
        {% endif %}
        
        {% if 'uniqueness' in column_config.checks %}
            {% do score_components.append("COALESCE((COUNT(DISTINCT " ~ column ~ ") * 100.0 / NULLIF(COUNT(*), 0)), 0)") %}
            {% set total_dimensions = total_dimensions + 1 %}
        {% endif %}
        
        {% if 'consistency' in column_config.checks and column_config.get('consistency_rule') %}
            {% do score_components.append("COALESCE((SUM(CASE WHEN " ~ column_config['consistency_rule'] ~ " THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0)), 0)") %}
            {% set total_dimensions = total_dimensions + 1 %}
        {% endif %}
        
        {% if validity_checks | length > 0 %}
            {% do score_components.append("COALESCE((SUM(" ~ validity_checks | join(' + ') ~ ") * 100.0 / (NULLIF(COUNT(*),0) * " ~ validity_checks | length ~ ")), 0)") %}
            {% set total_dimensions = total_dimensions + 1 %}
        {% endif %}
        
        {% if 'accuracy' in column_config.checks and column_config.get('accuracy_rule') %}
            {% do score_components.append("COALESCE((SUM(CASE WHEN " ~ column_config['accuracy_rule'] ~ " THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0)), 0)") %}
            {% set total_dimensions = total_dimensions + 1 %}
        {% endif %}
    {% endif %}
    
    {% if score_components | length > 0 %}
        (( {{ score_components | join(' + ') }} ) / {{ total_dimensions }}) AS column_score
    {% else %}
        NULL AS column_score
    {% endif %}
 
FROM {{ schema }}.{{ table }} 
{% endmacro %}