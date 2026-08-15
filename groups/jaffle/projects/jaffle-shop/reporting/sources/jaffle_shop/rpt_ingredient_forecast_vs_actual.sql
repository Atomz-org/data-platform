-- source extract for rpt_ingredient_forecast_vs_actual (PII columns excluded by the MDL projection)
select product_id, supply_id, supply_name, demand_week, actual_units, forecasted_units, actual_cost, forecasted_cost, forecast_variance_pct, forecast_error_pct, current_stock, daily_depletion_rate, estimated_days_of_stock
from main_marts.rpt_ingredient_forecast_vs_actual
