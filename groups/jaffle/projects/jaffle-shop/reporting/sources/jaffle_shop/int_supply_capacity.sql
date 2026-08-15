-- source extract for int_supply_capacity (PII columns excluded by the MDL projection)
select product_id, supply_demand_gap, weeks_of_supply, stock_status, total_stock_on_hand, stocked_locations, total_stock_value, weekly_demand_forecast, safety_stock_demand
from main_marts.int_supply_capacity
