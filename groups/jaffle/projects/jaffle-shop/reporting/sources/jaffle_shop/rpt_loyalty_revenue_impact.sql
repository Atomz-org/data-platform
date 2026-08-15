-- source extract for rpt_loyalty_revenue_impact (PII columns excluded by the MDL projection)
select order_month, is_loyalty_customer, total_revenue, total_orders, unique_customers, avg_order_value, month_total_revenue, month_total_orders, revenue_share, order_share, revenue_per_customer
from main_marts.rpt_loyalty_revenue_impact
