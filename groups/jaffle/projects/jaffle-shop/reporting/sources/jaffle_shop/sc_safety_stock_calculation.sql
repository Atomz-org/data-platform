-- source extract for sc_safety_stock_calculation (PII columns excluded by the MDL projection)
select product_id, location_id, daily_depletion_rate, current_quantity, global_avg_lead_time, global_lead_time_std, safety_stock_units, reorder_demand, excess_or_deficit
from main_marts.sc_safety_stock_calculation
