-- source extract for int_store_labor_demand (PII columns excluded by the MDL projection)
select location_id, day_of_week, day_name, avg_daily_orders, avg_labor_hours, avg_staff_count, avg_orders_per_labor_hour, predicted_labor_hours_needed
from main_marts.int_store_labor_demand
