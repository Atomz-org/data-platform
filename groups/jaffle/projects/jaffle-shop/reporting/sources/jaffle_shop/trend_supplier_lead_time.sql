-- source extract for trend_supplier_lead_time (PII columns excluded by the MDL projection)
select delivery_date, supplier_id, avg_lead_time, delivery_count, lead_time_7d_ma, lead_time_28d_ma, trend_direction
from main_marts.trend_supplier_lead_time
