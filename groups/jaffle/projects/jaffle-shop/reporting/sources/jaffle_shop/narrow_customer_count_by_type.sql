-- source extract for narrow_customer_count_by_type (PII columns excluded by the MDL projection)
select customer_type, customer_count
from main_marts.narrow_customer_count_by_type
