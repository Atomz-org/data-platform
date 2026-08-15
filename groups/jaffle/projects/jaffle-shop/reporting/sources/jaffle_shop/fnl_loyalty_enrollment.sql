-- source extract for fnl_loyalty_enrollment (PII columns excluded by the MDL projection)
select stage_1_total_customers, stage_2_loyalty_signups, stage_3_first_earn, stage_4_first_redemption, overall_conversion_pct, signup_rate_pct, earn_rate_pct, redemption_rate_pct
from main_marts.fnl_loyalty_enrollment
