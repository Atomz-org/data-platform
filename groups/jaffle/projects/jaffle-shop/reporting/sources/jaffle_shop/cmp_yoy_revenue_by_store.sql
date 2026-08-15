-- source extract for cmp_yoy_revenue_by_store (PII columns excluded by the MDL projection)
select location_id, current_month, current_revenue, prior_year_revenue, yoy_revenue_growth_pct, location_name, current_orders, prior_year_orders, revenue_change, yoy_order_growth_pct, current_avg_order_value, prior_year_avg_order_value
from main_marts.cmp_yoy_revenue_by_store
