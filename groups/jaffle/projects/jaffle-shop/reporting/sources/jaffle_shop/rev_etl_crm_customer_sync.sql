-- source extract for rev_etl_crm_customer_sync (PII columns excluded by the MDL projection)
select customer_id, customer_name, ltv_tier, lifetime_spend, total_orders, first_order_at, last_order_at, preferred_store_id, rfm_total_score, synced_at, source_system
from main_marts.rev_etl_crm_customer_sync
