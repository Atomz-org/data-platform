-- source extract for adv_consecutive_growth (PII columns excluded by the MDL projection)
select location_id, location_name, streak_start_month, streak_end_month, streak_length_months, min_monthly_revenue, max_monthly_revenue, streak_total_revenue, streak_rank
from main_marts.adv_consecutive_growth
