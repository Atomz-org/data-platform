-- source extract for int_supplier_order_frequency (PII columns excluded by the MDL projection)
select supplier_id, avg_days_between_orders, total_order_value, supplier_name, total_orders, first_order_date, last_order_date, days_span, avg_order_value
from main_marts.int_supplier_order_frequency
