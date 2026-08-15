-- source extract for fin_loyalty_program_cost (PII columns excluded by the MDL projection)
select txn_month, total_points_issued, total_points_redeemed, points_issued_cost, points_redeemed_value, loyalty_member_revenue, revenue_per_dollar_spent_on_loyalty, total_outstanding_points, outstanding_liability
from main_marts.fin_loyalty_program_cost
