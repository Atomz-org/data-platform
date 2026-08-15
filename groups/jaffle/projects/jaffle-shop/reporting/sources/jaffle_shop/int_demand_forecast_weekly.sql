-- source extract for int_demand_forecast_weekly (PII columns excluded by the MDL projection)
select product_id, sale_week, forecasted_quantity, forecast_error_pct, actual_quantity, actual_revenue, forecasted_revenue, quantity_volatility, recency_rank
from main_marts.int_demand_forecast_weekly
