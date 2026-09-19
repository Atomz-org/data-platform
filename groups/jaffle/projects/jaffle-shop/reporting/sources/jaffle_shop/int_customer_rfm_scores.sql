-- source extract for int_customer_rfm_scores (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    customer_id,
    recency_score,
    frequency_score,
    monetary_score,
    rfm_total_score,
    rfm_segment_code
from main_marts.int_customer_rfm_scores
