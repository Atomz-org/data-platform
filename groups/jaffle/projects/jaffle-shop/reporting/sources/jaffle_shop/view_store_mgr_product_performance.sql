-- source extract for view_store_mgr_product_performance (PII columns excluded by the MDL projection)
select store_id, product_id, sales_month, total_quantity, total_sales, product_rank_in_store
from main_marts.view_store_mgr_product_performance
