-- source extract for int_revenue_by_store_daily (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    revenue_date,
    location_id,
    location_name,
    store_opened_date,
    invoice_count,
    gross_revenue,
    total_revenue,
    rolling_7d_revenue,
    avg_7d_revenue,
    dod_growth_rate
from main_marts.int_revenue_by_store_daily
