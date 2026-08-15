-- source extract for rpt_staff_to_revenue_ratio (PII columns excluded by the MDL projection)
select location_id, month_start, revenue_per_employee, location_name, monthly_revenue, staff_count, staff_per_10k_revenue
from main_marts.rpt_staff_to_revenue_ratio
