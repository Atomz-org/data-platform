-- source extract for wide_order_with_customer (PII columns excluded by the MDL projection)
select order_id, ordered_at, order_total, tax_paid, location_id, customer_id, customer_name, customer_segment, lifetime_value, customer_total_orders, rfm_segment, loyalty_tier, churn_risk_score, first_order_date, days_since_last_order
from main_marts.wide_order_with_customer
