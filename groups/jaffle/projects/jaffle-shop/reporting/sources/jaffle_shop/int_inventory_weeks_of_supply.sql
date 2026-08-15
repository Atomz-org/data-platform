-- source extract for int_inventory_weeks_of_supply (PII columns excluded by the MDL projection)
select product_id, location_id, weeks_of_supply, supply_status, current_quantity, daily_depletion_rate, weekly_depletion_rate
from main_marts.int_inventory_weeks_of_supply
