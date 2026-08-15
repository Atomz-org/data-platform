-- source extract for rank_customers_by_recency (PII columns excluded by the MDL projection)
select customer_id, customer_name, days_since_last_order, total_orders, recency_rank, recency_decile, recency_band
from main_marts.rank_customers_by_recency
