-- source extract for view_store_mgr_staff_schedule (PII columns excluded by the MDL projection)
select shift_id, location_id, employee_id, full_name, position_title, shift_date, scheduled_start, scheduled_end, scheduled_hours, actual_hours, shift_status
from main_marts.view_store_mgr_staff_schedule
