-- source extract for adv_gap_analysis (PII columns excluded by the MDL projection)
select location_id, location_name, gap_start_date, gap_end_date, gap_days, previous_day_revenue
from main_marts.adv_gap_analysis
