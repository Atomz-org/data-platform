-- source extract for trend_po_volume (PII columns excluded by the MDL projection)
select ordered_at, po_count, po_total_value, po_count_7d_ma, po_value_7d_ma, po_count_28d_ma, po_value_28d_total, po_count_last_week
from main_marts.trend_po_volume
