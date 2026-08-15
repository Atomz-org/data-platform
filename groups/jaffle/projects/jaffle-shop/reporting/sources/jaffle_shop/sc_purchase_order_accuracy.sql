-- source extract for sc_purchase_order_accuracy (PII columns excluded by the MDL projection)
select accuracy_status, line_item_count, avg_variance_pct, total_variance_units
from main_marts.sc_purchase_order_accuracy
