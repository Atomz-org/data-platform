-- source extract for kpi_loyalty_enrollment_rate (PII columns excluded by the MDL projection)
select enrollment_month, new_enrollments, tracked_active_customers, enrollment_rate_pct
from main_marts.kpi_loyalty_enrollment_rate
