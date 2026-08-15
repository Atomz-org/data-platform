-- source extract for rpt_category_performance (PII columns excluded by the MDL projection)
select menu_category_id, category_name, parent_category_id, category_depth, product_count, total_units_sold, total_revenue, avg_daily_revenue, first_sale_date, last_sale_date, revenue_share_pct
from main_marts.rpt_category_performance
