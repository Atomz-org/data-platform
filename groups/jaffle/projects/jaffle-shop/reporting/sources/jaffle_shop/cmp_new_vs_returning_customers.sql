-- source extract for cmp_new_vs_returning_customers (PII columns excluded by the MDL projection)
select order_month, new_customers, returning_customers, returning_revenue_share_pct, returning_customer_share_pct, new_orders, new_revenue, new_avg_order_value, new_avg_items, returning_orders, returning_revenue, returning_avg_order_value, returning_avg_items
from main_marts.cmp_new_vs_returning_customers
