-- source extract for rpt_supplier_lead_time_trends (PII columns excluded by the MDL projection)
select supplier_id, order_month, order_count, avg_lead_time_days, min_lead_time_days, max_lead_time_days, avg_variance_days, monthly_on_time_rate, overall_avg_lead_time_days, overall_on_time_rate
from main_marts.rpt_supplier_lead_time_trends
