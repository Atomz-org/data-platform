-- source extract for sc_supplier_payment_terms (PII columns excluded by the MDL projection)
select supplier_id, supplier_name, total_pos, avg_payment_term_days, min_payment_term_days, max_payment_term_days, total_spend, completed_pos, implied_payment_terms
from main_marts.sc_supplier_payment_terms
