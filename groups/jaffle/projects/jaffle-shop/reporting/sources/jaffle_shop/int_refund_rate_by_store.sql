-- source extract for int_refund_rate_by_store (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    location_id,
    report_month,
    invoice_count,
    total_invoice_amount,
    refund_count,
    total_refund_amount,
    refund_rate,
    refund_amount_rate,
    avg_days_to_resolution
from main_marts.int_refund_rate_by_store
