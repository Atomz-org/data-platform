-- source extract for rev_etl_email_segment_high_value (PII columns excluded by the MDL projection)
select customer_id, customer_name, lifetime_spend, total_orders, ltv_tier, preferred_store_id, email_segment, exported_at
from main_marts.rev_etl_email_segment_high_value
