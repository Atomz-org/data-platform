-- source extract for int_supplier_payment_aging (PII columns excluded by the MDL projection)
select supplier_id, avg_days_payable_outstanding, total_outstanding, supplier_name, total_pos, amount_0_30, amount_31_60, amount_61_90, amount_over_90
from main_marts.int_supplier_payment_aging
