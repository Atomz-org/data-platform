-- source extract for fnl_new_customer_onboarding (PII columns excluded by the MDL projection)
select cohort_month, stage_1_first_order, stage_2_second_within_30d, stage_3_third_order, second_order_rate_pct, avg_days_to_second_order, stage_2b_second_order_ever, stage_4_loyalty_signup, third_order_rate_pct
from main_marts.fnl_new_customer_onboarding
