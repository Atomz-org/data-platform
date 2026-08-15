-- source extract for adv_excluding_current_avg (PII columns excluded by the MDL projection)
select revenue_date, location_id, location_name, total_revenue, invoice_count, peer_days_count, peer_avg_revenue_6d, inclusive_avg_revenue_7d, deviation_from_peer_avg, pct_deviation_from_peer, is_anomaly, anomaly_type
from main_marts.adv_excluding_current_avg
