-- source extract for rpt_seasonal_demand_pattern (PII columns excluded by the MDL projection)
select product_id, supply_id, supply_name, month_of_year, avg_monthly_units, avg_monthly_cost, months_of_data, overall_avg_units, seasonality_index
from main_marts.rpt_seasonal_demand_pattern
