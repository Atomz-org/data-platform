-- source extract for kpi_avg_customer_lifetime (PII columns excluded by the MDL projection)
select total_customers, avg_tenure_days, avg_repeat_tenure_days, avg_ltv, avg_order_count, avg_aov
from main_marts.kpi_avg_customer_lifetime
