-- source extract for rank_customers_by_basket_size (PII columns excluded by the MDL projection)
select customer_id, customer_name, avg_order_value, total_orders, basket_rank, basket_decile
from main_marts.rank_customers_by_basket_size
