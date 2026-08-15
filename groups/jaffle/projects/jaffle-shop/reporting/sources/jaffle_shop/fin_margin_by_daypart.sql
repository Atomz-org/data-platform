-- source extract for fin_margin_by_daypart (PII columns excluded by the MDL projection)
select location_id, daypart, order_month, total_revenue, total_margin, gross_margin_pct, item_count
from main_marts.fin_margin_by_daypart
