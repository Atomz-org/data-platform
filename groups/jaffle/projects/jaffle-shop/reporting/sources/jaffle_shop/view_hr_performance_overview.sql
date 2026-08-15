-- source extract for view_hr_performance_overview (PII columns excluded by the MDL projection)
select employee_id, performance_score, productivity_score, attendance_score, training_score, performance_tier, performance_band, performance_percentile
from main_marts.view_hr_performance_overview
