-- source extract for view_store_mgr_customer_insights (PII columns excluded by the MDL projection)
select store_id, ltv_tier, customer_count, avg_ltv, avg_orders_at_store, total_orders_at_store
from main_marts.view_store_mgr_customer_insights
