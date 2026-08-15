-- source extract for geo_store_cluster_analysis (PII columns excluded by the MDL projection)
select location_id, store_name, avg_monthly_revenue, avg_margin_pct, revenue_tier, margin_tier, cluster_label, cluster_description
from main_marts.geo_store_cluster_analysis
