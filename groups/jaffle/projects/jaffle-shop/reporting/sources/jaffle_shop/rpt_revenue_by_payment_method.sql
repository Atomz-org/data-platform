-- source extract for rpt_revenue_by_payment_method (PII columns excluded by the MDL projection)
select payment_method, location_id, revenue_month, order_count, transaction_count, payment_method_revenue, total_location_revenue, revenue_share_pct
from main_marts.rpt_revenue_by_payment_method
