-- source extract for hr_seasonal_hiring_pattern (PII columns excluded by the MDL projection)
select hire_month_num, avg_monthly_hires, min_monthly_hires, max_monthly_hires, years_of_data, global_avg, seasonal_index, hiring_season
from main_marts.hr_seasonal_hiring_pattern
