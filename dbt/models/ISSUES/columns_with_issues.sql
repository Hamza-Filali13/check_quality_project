SELECT *
FROM {{ ref('column_kpi') }}
WHERE completeness_score < 100
   OR uniqueness_score < 100
   OR (consistency_score IS NOT NULL AND consistency_score < 100)
   OR (validity_score IS NOT NULL AND validity_score < 100)
