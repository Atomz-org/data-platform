-- source extract for dq_negative_balances (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    account_id,
    current_balance,
    balance_type
from main_marts.dq_negative_balances
