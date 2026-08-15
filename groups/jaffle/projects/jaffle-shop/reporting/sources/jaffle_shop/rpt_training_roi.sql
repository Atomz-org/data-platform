-- source extract for rpt_training_roi (PII columns excluded by the MDL projection)
select compliance_tier, employee_count, avg_performance_score, avg_rolling_performance, avg_courses_completed, avg_training_score, avg_tenure_days, improving_count, declining_count, stable_count, improving_pct
from main_marts.rpt_training_roi
