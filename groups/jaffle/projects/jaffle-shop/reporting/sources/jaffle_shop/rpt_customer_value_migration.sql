-- source extract for rpt_customer_value_migration (PII columns excluded by the MDL projection)
select spend_month, prev_segment, current_segment, customer_count, total_spend
from main_marts.rpt_customer_value_migration
