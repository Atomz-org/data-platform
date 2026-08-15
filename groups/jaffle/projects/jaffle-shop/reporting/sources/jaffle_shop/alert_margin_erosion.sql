-- source extract for alert_margin_erosion (PII columns excluded by the MDL projection)
select sale_month, gross_margin_pct, margin_3m_avg, margin_vs_avg, alert_type, severity
from main_marts.alert_margin_erosion
