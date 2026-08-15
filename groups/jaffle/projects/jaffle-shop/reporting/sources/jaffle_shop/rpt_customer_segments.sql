-- source extract for rpt_customer_segments (PII columns excluded by the MDL projection)
select customer_segment, customer_count, segment_pct, avg_spend, avg_orders, avg_days_since_last_order, avg_rfm_score, total_segment_revenue, segment_revenue_share_pct
from main_marts.rpt_customer_segments
