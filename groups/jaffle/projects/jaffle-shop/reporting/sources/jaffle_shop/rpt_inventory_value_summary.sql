-- source extract for rpt_inventory_value_summary (PII columns excluded by the MDL projection)
select warehouse_id, warehouse_name, product_id, product_name, product_type, total_quantity, total_value, avg_unit_cost, warehouse_total_value, value_share_of_warehouse
from main_marts.rpt_inventory_value_summary
