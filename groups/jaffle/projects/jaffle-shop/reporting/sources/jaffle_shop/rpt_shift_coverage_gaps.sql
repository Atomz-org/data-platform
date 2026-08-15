-- source extract for rpt_shift_coverage_gaps (PII columns excluded by the MDL projection)
select location_id, location_name, day_of_week, total_occurrences, understaffed_occurrences, avg_coverage_pct, avg_hours_gap, is_chronic_gap
from main_marts.rpt_shift_coverage_gaps
