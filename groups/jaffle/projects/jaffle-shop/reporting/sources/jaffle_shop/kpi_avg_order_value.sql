-- source extract for kpi_avg_order_value (PII columns excluded by the MDL projection)
select month_start, location_id, monthly_revenue, monthly_orders, avg_order_value, prior_month_aov
from main_marts.kpi_avg_order_value
