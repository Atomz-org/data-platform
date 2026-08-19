-- source extract for int_refund_processing_time (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    refund_id,
    processing_days,
    processing_speed_tier
from main_marts.int_refund_processing_time
