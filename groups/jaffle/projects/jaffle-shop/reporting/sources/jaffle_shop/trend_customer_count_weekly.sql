-- source extract for trend_customer_count_weekly (PII columns excluded by the MDL projection)
select activity_week, active_customers, new_customers, returning_customers, customers_4w_ma, new_customers_4w_ma, prev_week_customers, wow_growth_pct
from main_marts.trend_customer_count_weekly
