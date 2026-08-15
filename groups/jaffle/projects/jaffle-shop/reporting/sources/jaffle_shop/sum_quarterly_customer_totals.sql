-- source extract for sum_quarterly_customer_totals (PII columns excluded by the MDL projection)
select metric_quarter, total_customer_months, total_new_customers, avg_monthly_customers
from main_marts.sum_quarterly_customer_totals
