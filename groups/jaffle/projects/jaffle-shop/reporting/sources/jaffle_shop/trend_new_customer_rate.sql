-- source extract for trend_new_customer_rate (PII columns excluded by the MDL projection)
select activity_date, total_active, new_customers, new_customer_rate_pct, new_cust_7d_ma, new_cust_28d_ma, new_cust_7d_total, acquisition_momentum
from main_marts.trend_new_customer_rate
