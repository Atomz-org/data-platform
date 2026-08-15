-- source extract for fin_coupon_cost_analysis (PII columns excluded by the MDL projection)
select campaign_id, campaign_name, campaign_channel, redemption_month, redemption_count, total_discount_cost, avg_discount_per_redemption, min_discount, max_discount, cumulative_discount_cost
from main_marts.fin_coupon_cost_analysis
