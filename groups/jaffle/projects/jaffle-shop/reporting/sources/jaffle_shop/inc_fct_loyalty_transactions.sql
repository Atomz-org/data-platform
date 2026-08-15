-- source extract for inc_fct_loyalty_transactions (PII columns excluded by the MDL projection)
select loyalty_transaction_id, loyalty_member_id, transaction_type, points, transacted_at, order_id, transaction_month
from main_marts.inc_fct_loyalty_transactions
