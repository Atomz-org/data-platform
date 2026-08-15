-- source extract for met_daily_waste_metrics (PII columns excluded by the MDL projection)
select waste_date, location_id, total_waste_cost, location_name, waste_events, total_quantity_wasted, distinct_products_wasted, distinct_waste_reasons
from main_marts.met_daily_waste_metrics
