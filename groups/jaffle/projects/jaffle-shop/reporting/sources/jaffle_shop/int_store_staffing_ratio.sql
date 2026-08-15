-- source extract for int_store_staffing_ratio (PII columns excluded by the MDL projection)
select location_id, location_name, shift_date, scheduled_staff_count, total_scheduled_hours, order_count, staff_hours_per_order, orders_per_staff
from main_marts.int_store_staffing_ratio
