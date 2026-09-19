-- source extract for ml_feature_employee_attrition (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    employee_id,
    tenure_days,
    avg_orders_per_hour,
    avg_weekly_overtime,
    overtime_frequency_pct,
    training_completion_pct,
    attrition_label
from main_marts.ml_feature_employee_attrition
