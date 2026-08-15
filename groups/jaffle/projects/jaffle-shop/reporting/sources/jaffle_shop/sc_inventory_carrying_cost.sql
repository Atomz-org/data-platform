-- source extract for sc_inventory_carrying_cost (PII columns excluded by the MDL projection)
select product_id, location_id, location_name, current_quantity, unit_value, inventory_value, monthly_carrying_cost, annual_carrying_cost
from main_marts.sc_inventory_carrying_cost
