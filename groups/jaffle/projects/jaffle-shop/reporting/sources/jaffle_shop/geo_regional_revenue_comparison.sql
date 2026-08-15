-- source extract for geo_regional_revenue_comparison (PII columns excluded by the MDL projection)
select revenue_group, store_count, group_avg_monthly_revenue, group_total_avg_revenue, group_min_avg_revenue, group_max_avg_revenue, diff_from_median
from main_marts.geo_regional_revenue_comparison
