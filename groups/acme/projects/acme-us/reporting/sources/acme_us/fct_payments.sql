-- source extract for fct_payments (PII columns excluded by the MDL projection)
select payment_id, amount, paid_at, currency_code, payment_status, customer_segment, country_code, plan_tier
from main_marts.fct_payments
