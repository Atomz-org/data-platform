-- source extract for rpt_loyalty_program_comprehensive (PII columns excluded by the MDL projection)
select report_month, new_enrollments, monthly_redemption_rate, active_members_enrolled, active_members_transacting, total_points_earned, total_points_redeemed, total_transactions
from main_marts.rpt_loyalty_program_comprehensive
