-- source extract for int_product_review_trend (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    product_id,
    review_month,
    avg_rating,
    rolling_3m_avg_rating,
    rating_tier
from main_marts.int_product_review_trend
