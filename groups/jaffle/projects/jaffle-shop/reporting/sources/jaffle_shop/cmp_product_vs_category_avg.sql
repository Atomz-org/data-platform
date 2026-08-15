-- source extract for cmp_product_vs_category_avg (PII columns excluded by the MDL projection)
select product_id, product_name, category_name, revenue_vs_category, revenue_index, margin_vs_category_pp, total_units_sold, total_revenue, product_margin_pct, cat_avg_units, cat_avg_revenue, cat_avg_margin_pct, products_in_category, units_vs_category, units_index
from main_marts.cmp_product_vs_category_avg
