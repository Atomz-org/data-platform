-- source extract for rank_customers_by_ltv (PII columns excluded by the MDL projection)
select customer_id, customer_name, lifetime_spend, total_orders, avg_order_value, ltv_rank, ltv_decile, revenue_share_pct, cumulative_revenue
from main_marts.rank_customers_by_ltv
