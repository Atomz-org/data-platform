-- source extract for inc_fct_orders (PII columns excluded by the MDL projection)
select order_id, customer_id, customer_name, location_id, location_name, ordered_at, order_total, tax_paid, subtotal, order_date, order_month, order_hour, order_day_of_week
from main_marts.inc_fct_orders
