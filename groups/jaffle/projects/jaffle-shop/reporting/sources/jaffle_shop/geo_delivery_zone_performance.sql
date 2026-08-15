-- source extract for geo_delivery_zone_performance (PII columns excluded by the MDL projection)
select location_id, performance_month, zone_revenue, active_days, avg_total_revenue, min_total_revenue, max_total_revenue, total_revenue_range, revenue_per_active_day
from main_marts.geo_delivery_zone_performance
