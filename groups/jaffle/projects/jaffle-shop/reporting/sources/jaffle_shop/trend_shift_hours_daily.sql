-- source extract for trend_shift_hours_daily (PII columns excluded by the MDL projection)
select shift_date, location_id, shift_count, total_hours, avg_shift_length, hours_7d_ma, hours_28d_ma, avg_length_7d_ma
from main_marts.trend_shift_hours_daily
