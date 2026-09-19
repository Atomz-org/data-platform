-- source extract for int_customer_preferred_store (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    customer_id,
    preferred_store_id,
    preferred_store_visit_pct,
    distinct_stores_visited
from main_marts.int_customer_preferred_store
