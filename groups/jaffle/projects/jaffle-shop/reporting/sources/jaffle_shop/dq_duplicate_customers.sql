-- source extract for dq_duplicate_customers (PII columns excluded by the MDL projection)
select customer_id, customer_name, name_occurrences, duplicate_rank
from main_marts.dq_duplicate_customers
