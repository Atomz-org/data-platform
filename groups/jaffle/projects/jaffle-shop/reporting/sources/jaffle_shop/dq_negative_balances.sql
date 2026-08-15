-- source extract for dq_negative_balances (PII columns excluded by the MDL projection)
select account_id, current_balance, balance_type, card_number, customer_id, account_status, initial_balance
from main_marts.dq_negative_balances
