-- source extract for rpt_supply_demand_alignment (PII columns excluded by the MDL projection)
select product_id, supply_demand_ratio, alignment_status, product_name, product_type, current_supply, total_demand, supply_locations, supply_demand_gap
from main_marts.rpt_supply_demand_alignment
