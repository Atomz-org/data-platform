-- source extract for met_weekly_revenue_by_store (PII columns excluded by the MDL projection)
select week_start, location_id, wow_revenue_growth, store_name, weekly_revenue, weekly_orders, weekly_gross_revenue, weekly_tax_collected, avg_order_value, prev_week_revenue
from main_marts.met_weekly_revenue_by_store
