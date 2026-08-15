-- source extract for rank_customers_by_frequency (PII columns excluded by the MDL projection)
select customer_id, customer_name, total_orders, lifetime_spend, frequency_rank, frequency_decile
from main_marts.rank_customers_by_frequency
