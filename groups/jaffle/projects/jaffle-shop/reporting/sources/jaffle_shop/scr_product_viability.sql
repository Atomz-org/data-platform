-- source extract for scr_product_viability (PII columns excluded by the MDL projection)
select product_id, viability_score, viability_tier, product_name, product_type, total_units_sold, total_revenue, active_sale_days, sales_score, margin_score, review_score, availability_score, gross_margin_pct, avg_review_rating, total_reviews, inventory_on_hand
from main_marts.scr_product_viability
