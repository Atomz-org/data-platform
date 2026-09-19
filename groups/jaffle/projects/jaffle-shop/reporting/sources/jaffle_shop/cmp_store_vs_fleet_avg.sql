-- source extract for cmp_store_vs_fleet_avg (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    location_id,
    store_name,
    store_revenue,
    fleet_avg_revenue,
    revenue_vs_fleet_pct,
    margin_vs_fleet_pp,
    revenue_rank
from main_marts.cmp_store_vs_fleet_avg
