-- source extract for int_customer_preferred_store (PII columns excluded by the MDL projection)
select customer_id, preferred_store_id, preferred_store_visit_pct, distinct_stores_visited, preferred_store_name, preferred_store_visits, preferred_store_spend, preferred_store_first_visit, preferred_store_last_visit
from main_marts.int_customer_preferred_store
