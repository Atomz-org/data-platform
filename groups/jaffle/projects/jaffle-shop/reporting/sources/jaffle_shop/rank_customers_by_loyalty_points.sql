-- source extract for rank_customers_by_loyalty_points (PII columns excluded by the MDL projection)
select customer_id, loyalty_member_id, points_balance, current_tier_name, points_rank, points_decile
from main_marts.rank_customers_by_loyalty_points
