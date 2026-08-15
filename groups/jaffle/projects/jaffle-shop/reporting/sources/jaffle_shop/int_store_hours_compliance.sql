-- source extract for int_store_hours_compliance (PII columns excluded by the MDL projection)
select location_id, work_date, compliance_status, day_name, posted_open_time, posted_close_time, earliest_clock_in, latest_clock_out, employees_on_duty, should_be_closed
from main_marts.int_store_hours_compliance
