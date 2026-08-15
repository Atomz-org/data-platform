-- source extract for met_monthly_waste_metrics (PII columns excluded by the MDL projection)
select month_start, location_id, waste_to_revenue_pct, mom_waste_cost_change, location_name, monthly_waste_events, monthly_quantity_wasted, monthly_waste_cost, avg_daily_products_wasted, monthly_revenue, prev_month_waste_cost
from main_marts.met_monthly_waste_metrics
