-- source extract for int_seasonal_inventory_needs (PII columns excluded by the MDL projection)
select product_id, demand_month, seasonal_index, season_classification, monthly_forecasted_demand, avg_volatility, safety_stock_demand, avg_monthly_demand
from main_marts.int_seasonal_inventory_needs
