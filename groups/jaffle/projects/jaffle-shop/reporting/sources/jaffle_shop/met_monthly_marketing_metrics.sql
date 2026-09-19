-- source extract for met_monthly_marketing_metrics (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    month_start,
    total_marketing_spend,
    coupon_redemptions
from main_marts.met_monthly_marketing_metrics
