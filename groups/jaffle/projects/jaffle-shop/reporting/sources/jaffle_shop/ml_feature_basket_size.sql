-- source extract for ml_feature_basket_size (PII columns excluded by the MDL projection)
select order_id, customer_id, store_id, customer_rfm_segment, loyalty_tier, is_weekend, promo_active, basket_size, ordered_at, order_total, subtotal, item_count, ltv_tier, day_of_week, day_name, month_of_year
from main_marts.ml_feature_basket_size
