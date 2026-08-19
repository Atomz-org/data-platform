-- source extract for int_product_review_summary (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    product_id,
    total_review_count,
    avg_rating,
    positive_review_count,
    neutral_review_count,
    negative_review_count,
    positive_review_pct,
    negative_review_pct,
    first_review_date,
    last_review_date
from main_marts.int_product_review_summary
