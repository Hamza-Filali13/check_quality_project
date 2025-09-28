SELECT *
FROM {{ ref('column_kpi') }}
WHERE column_score < 100
ORDER BY table_name, column_score
