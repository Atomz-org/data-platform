-- source extract for mkt_loyalty_tier_value (PII columns excluded by the MDL projection)
select current_tier_name, member_count, avg_lifetime_spend, avg_order_count, avg_order_value, total_tier_revenue, incremental_value_vs_lower_tier, revenue_share_pct
from main_marts.mkt_loyalty_tier_value
