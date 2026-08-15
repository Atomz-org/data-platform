-- source extract for poc_supplier_spend_mom (PII columns excluded by the MDL projection)
select order_month, supplier_id, current_spend, prior_month_spend, current_pos, prior_month_pos, spend_mom_pct
from main_marts.poc_supplier_spend_mom
