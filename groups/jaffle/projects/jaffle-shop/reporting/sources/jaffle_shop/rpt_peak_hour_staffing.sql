-- source extract for rpt_peak_hour_staffing (PII columns excluded by the MDL projection)
select store_id, order_hour, hour_classification, avg_orders_per_hour, avg_revenue_per_hour, hour_share_of_total_pct, current_avg_staff, current_staffing_ratio, recommended_staff, staffing_gap, staffing_recommendation
from main_marts.rpt_peak_hour_staffing
