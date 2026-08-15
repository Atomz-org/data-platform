-- source extract for mkt_loyalty_program_break_even (PII columns excluded by the MDL projection)
select txn_month, points_earned, points_redeemed, cumulative_earned, cumulative_redeemed, outstanding_points, cumulative_redemption_rate_pct, estimated_breakage_value_dollars, monthly_cost_dollars, monthly_redemption_value_dollars
from main_marts.mkt_loyalty_program_break_even
