-- source extract for rpt_demand_planning_dashboard (PII columns excluded by the MDL projection)
select product_id, product_name, total_stock_on_hand, stocked_locations, total_stock_value, weekly_demand_forecast, safety_stock_demand, supply_demand_gap, weeks_of_supply, stock_status, avg_recent_demand, avg_forecast_error, max_volatility, demand_trend_pct, action_priority, recommended_action
from main_marts.rpt_demand_planning_dashboard
