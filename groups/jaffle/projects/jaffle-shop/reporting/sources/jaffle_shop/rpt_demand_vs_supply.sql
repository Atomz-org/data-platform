-- source extract for rpt_demand_vs_supply (PII columns excluded by the MDL projection)
select product_id, location_id, current_quantity, daily_demand_rate, demand_last_30d, total_supply, total_demand, estimated_days_of_stock, supply_to_demand_ratio, supply_demand_status, last_movement_at
from main_marts.rpt_demand_vs_supply
