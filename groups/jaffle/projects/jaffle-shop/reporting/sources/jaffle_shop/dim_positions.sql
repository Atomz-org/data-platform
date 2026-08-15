-- source extract for dim_positions (PII columns excluded by the MDL projection)
select position_id, department_id, position_title, pay_grade, min_hourly_rate, max_hourly_rate, is_management, pay_range_spread
from main_marts.dim_positions
