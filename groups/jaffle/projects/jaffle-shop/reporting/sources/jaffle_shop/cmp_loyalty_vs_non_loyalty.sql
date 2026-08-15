-- source extract for cmp_loyalty_vs_non_loyalty (PII columns excluded by the MDL projection)
select customer_segment, customer_count, avg_lifetime_spend, avg_total_orders, repeat_rate_pct, revenue_share_pct, avg_order_value, avg_days_since_last_order, avg_rfm_score, avg_tenure_days, total_segment_revenue, repeat_customers, customer_share_pct
from main_marts.cmp_loyalty_vs_non_loyalty
