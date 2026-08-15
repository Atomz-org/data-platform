-- source extract for int_ingredient_sourcing_options (PII columns excluded by the MDL projection)
select product_id, supplier_id, cost_rank, available_supplier_count, supplier_name, supplier_is_active, order_count, avg_unit_cost, min_unit_cost, max_unit_cost, total_quantity_ordered, last_order_date
from main_marts.int_ingredient_sourcing_options
