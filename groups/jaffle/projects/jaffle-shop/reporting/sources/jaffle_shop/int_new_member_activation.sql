-- source extract for int_new_member_activation (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    loyalty_member_id,
    days_to_first_transaction,
    activation_speed
from main_marts.int_new_member_activation
