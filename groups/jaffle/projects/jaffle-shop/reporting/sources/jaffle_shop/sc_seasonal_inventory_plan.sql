-- source extract for sc_seasonal_inventory_plan (PII columns excluded by the MDL projection)
select product_id, calendar_month, avg_monthly_qty, overall_avg_qty, seasonal_factor, recommended_monthly_stock, demand_season
from main_marts.sc_seasonal_inventory_plan
