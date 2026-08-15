-- source extract for sc_procurement_calendar (PII columns excluded by the MDL projection)
select day_of_week, po_count, total_spend, avg_po_value, pct_of_total_pos, day_category
from main_marts.sc_procurement_calendar
