-- source extract for rpt_customer_value_migration (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    spend_month,
    prev_segment,
    current_segment,
    customer_count
from main_marts.rpt_customer_value_migration
