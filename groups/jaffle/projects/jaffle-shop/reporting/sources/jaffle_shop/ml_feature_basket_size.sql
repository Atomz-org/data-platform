-- source extract for ml_feature_basket_size (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    order_id,
    customer_id,
    store_id,
    customer_rfm_segment,
    loyalty_tier,
    is_weekend,
    promo_active,
    basket_size
from main_marts.ml_feature_basket_size
