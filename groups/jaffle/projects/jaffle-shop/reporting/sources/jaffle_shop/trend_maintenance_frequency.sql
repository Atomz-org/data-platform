-- source extract for trend_maintenance_frequency (PII columns excluded by the MDL projection)
select completed_date, location_id, maintenance_events, total_cost, events_28d_ma, cost_28d_ma, events_90d_total, maintenance_alert
from main_marts.trend_maintenance_frequency
