-- source extract for sum_monthly_store_totals (PII columns excluded by the MDL projection)
select month_start, location_id, monthly_revenue, monthly_orders, avg_order_value, labor_cost, waste_cost, net_contribution, prior_month_revenue
from main_marts.sum_monthly_store_totals
