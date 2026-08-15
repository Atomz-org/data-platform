-- source extract for sc_supplier_lead_time_trend (PII columns excluded by the MDL projection)
select supplier_id, supplier_name, month_start, avg_lead_time_days, lead_time_std_dev, prev_month_lead_time, lead_time_3m_avg, lead_time_change, trend_direction
from main_marts.sc_supplier_lead_time_trend
