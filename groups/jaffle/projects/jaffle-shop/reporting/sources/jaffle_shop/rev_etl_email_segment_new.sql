-- source extract for rev_etl_email_segment_new (PII columns excluded by the MDL projection)
select customer_id, customer_name, first_order_at, total_orders, lifetime_spend, preferred_store_id, email_segment, exported_at
from main_marts.rev_etl_email_segment_new
