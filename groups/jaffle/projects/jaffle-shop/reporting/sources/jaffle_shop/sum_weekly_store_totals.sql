-- source extract for sum_weekly_store_totals (PII columns excluded by the MDL projection)
select week_start, location_id, weekly_revenue, weekly_orders, avg_order_value, labor_cost, prior_week_revenue
from main_marts.sum_weekly_store_totals
