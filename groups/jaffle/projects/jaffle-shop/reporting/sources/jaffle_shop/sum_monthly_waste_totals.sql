-- source extract for sum_monthly_waste_totals (PII columns excluded by the MDL projection)
select month_start, location_id, monthly_waste_events, avg_waste_per_event, prior_month_waste
from main_marts.sum_monthly_waste_totals
