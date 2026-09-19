-- source extract for ml_feature_store_sales (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    store_id,
    month_start,
    monthly_revenue,
    trailing_3m_avg_revenue,
    trailing_6m_avg_revenue,
    same_month_prior_year,
    staff_count
from main_marts.ml_feature_store_sales
