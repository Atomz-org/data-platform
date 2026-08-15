-- source extract for int_labor_utilization_rate (PII columns excluded by the MDL projection)
select location_id, work_date, orders_per_labor_hour, utilization_tier, total_clocked_hours, order_count
from main_marts.int_labor_utilization_rate
