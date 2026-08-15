-- source extract for int_ingredient_demand_forecast (PII columns excluded by the MDL projection)
select product_id, supply_id, supply_name, demand_week, units_ordered, forecast_units_4wk_avg, forecast_cost_4wk_avg, total_ingredient_cost
from main_marts.int_ingredient_demand_forecast
