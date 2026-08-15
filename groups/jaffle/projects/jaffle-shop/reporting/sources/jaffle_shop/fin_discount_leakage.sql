-- source extract for fin_discount_leakage (PII columns excluded by the MDL projection)
select redemption_month, total_discount_given, budgeted_marketing_spend, discount_variance, discount_utilization_pct, leakage_flag
from main_marts.fin_discount_leakage
