-- source extract for sc_landed_cost_analysis (PII columns excluded by the MDL projection)
select product_id, supplier_id, total_purchase_cost, total_quantity_purchased, allocated_delivery_cost, product_cost_of_waste, total_landed_cost, landed_cost_per_unit, raw_cost_per_unit
from main_marts.sc_landed_cost_analysis
