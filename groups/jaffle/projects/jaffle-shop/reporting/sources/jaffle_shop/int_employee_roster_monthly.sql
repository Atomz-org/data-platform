-- source extract for int_employee_roster_monthly (PII columns excluded by the MDL projection)
select month_start, location_id, headcount, management_count, new_hires_in_month, terminations_in_month, non_management_count
from main_marts.int_employee_roster_monthly
