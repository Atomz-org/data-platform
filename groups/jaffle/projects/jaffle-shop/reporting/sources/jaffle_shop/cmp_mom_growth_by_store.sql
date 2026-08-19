-- source extract for cmp_mom_growth_by_store (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    location_id,
    current_month,
    mom_revenue_growth_pct,
    mom_order_growth_pct,
    trailing_3m_avg_revenue
from main_marts.cmp_mom_growth_by_store
