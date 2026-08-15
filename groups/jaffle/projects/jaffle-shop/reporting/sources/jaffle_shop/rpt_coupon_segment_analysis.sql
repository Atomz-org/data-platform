-- source extract for rpt_coupon_segment_analysis (PII columns excluded by the MDL projection)
select customer_segment, total_redemptions, unique_customers, total_discount_given, total_order_revenue, total_net_revenue, avg_discount_per_redemption, avg_order_value, redemptions_per_customer, redemption_share, revenue_share, net_revenue_per_customer, discount_efficiency_ratio
from main_marts.rpt_coupon_segment_analysis
