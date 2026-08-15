-- source extract for scr_menu_item_ranking (PII columns excluded by the MDL projection)
select product_id, composite_score, overall_composite_rank, category_composite_rank, product_name, product_type, category_name, total_units_sold, total_revenue, overall_volume_rank, overall_revenue_rank, volume_rank_in_category, revenue_rank_in_category, gross_margin, gross_margin_pct, avg_rating, total_reviews, positive_review_pct
from main_marts.scr_menu_item_ranking
