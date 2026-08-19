-- source extract for cmp_weekday_vs_weekend (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    location_id,
    weekday_avg_revenue_per_day,
    weekend_avg_revenue_per_day,
    weekend_revenue_lift_pct,
    weekend_ticket_lift_pct
from main_marts.cmp_weekday_vs_weekend
