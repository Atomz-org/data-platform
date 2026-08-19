-- source extract for int_payment_decline_rate (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    location_id,
    payment_method,
    decline_rate_pct
from main_marts.int_payment_decline_rate
