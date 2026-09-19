-- source extract for dq_duplicate_customers (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    customer_id,
    customer_name,
    name_occurrences
from main_marts.dq_duplicate_customers
