-- source extract for int_category_sales_share (PII columns excluded by the MDL projection)
select category, location_id, revenue_share_pct, category_revenue, category_quantity, store_total_revenue
from main_marts.int_category_sales_share
