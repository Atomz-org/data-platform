-- source extract for dist_employee_tenure (PII columns excluded by the MDL projection)
select tenure_bucket, employee_count, avg_tenure, mean_tenure, median_tenure
from main_marts.dist_employee_tenure
