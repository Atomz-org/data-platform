-- source extract for rpt_product_sales_by_store (PII columns excluded by the MDL projection)
select location_id, location_name, product_id, product_name, product_type, total_units_sold, total_revenue, avg_daily_units, active_sale_days, first_sale_date, last_sale_date, volume_rank_at_store, revenue_rank_at_store, revenue_share_at_store
from main_marts.rpt_product_sales_by_store
