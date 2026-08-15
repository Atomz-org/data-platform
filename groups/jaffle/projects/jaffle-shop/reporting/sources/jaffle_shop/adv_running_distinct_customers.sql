-- source extract for adv_running_distinct_customers (PII columns excluded by the MDL projection)
select date_day, orders_today, revenue_today, active_customers_today, new_customers_today, cumulative_distinct_customers
from main_marts.adv_running_distinct_customers
