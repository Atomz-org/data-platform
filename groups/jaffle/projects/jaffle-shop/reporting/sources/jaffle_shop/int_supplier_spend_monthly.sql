-- source extract for int_supplier_spend_monthly (PII columns excluded by the MDL projection)
select supplier_id, supplier_name, order_month, count_purchase_orders, total_spend, avg_unit_cost, total_quantity_ordered
from main_marts.int_supplier_spend_monthly
