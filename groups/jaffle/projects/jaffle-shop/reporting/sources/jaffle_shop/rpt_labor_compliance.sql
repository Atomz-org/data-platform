-- source extract for rpt_labor_compliance (PII columns excluded by the MDL projection)
select employee_id, store_id, week_start, weekly_hours_worked, violation_type
from main_marts.rpt_labor_compliance
