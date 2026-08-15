-- source extract for rpt_financial_anomaly_detection (PII columns excluded by the MDL projection)
select store_name, store_id, report_month, total_revenue, revenue_change_pct, net_margin_pct, refund_count, refund_rate_pct, fleet_avg_refund_rate, is_revenue_drop_anomaly, is_refund_rate_anomaly, is_negative_margin_anomaly, anomaly_severity, anomaly_count
from main_marts.rpt_financial_anomaly_detection
