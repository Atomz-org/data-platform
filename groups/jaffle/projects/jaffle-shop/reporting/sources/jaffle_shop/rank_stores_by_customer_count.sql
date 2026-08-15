-- source extract for rank_stores_by_customer_count (PII columns excluded by the MDL projection)
select order_month, location_id, customer_count, customer_rank, customer_quartile
from main_marts.rank_stores_by_customer_count
