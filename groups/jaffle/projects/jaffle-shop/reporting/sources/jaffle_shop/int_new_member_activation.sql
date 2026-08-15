-- source extract for int_new_member_activation (PII columns excluded by the MDL projection)
select loyalty_member_id, days_to_first_transaction, activation_speed, customer_id, enrolled_at, first_transaction_date
from main_marts.int_new_member_activation
