-- source extract for fnl_refund_to_resolution (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    refund_month,
    total_refund_requests,
    approved,
    denied,
    approval_rate_pct,
    avg_days_to_resolution
from main_marts.fnl_refund_to_resolution
