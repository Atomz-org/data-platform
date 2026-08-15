-- source extract for int_supplier_contract_expiry (PII columns excluded by the MDL projection)
select contract_id, days_until_expiry, expiry_urgency, supplier_id, supplier_name, contract_type, payment_terms, minimum_order_amount, lead_time_days, effective_date, expiration_date
from main_marts.int_supplier_contract_expiry
