-- source extract for rpt_customer_effort_score_proxy (PII columns excluded by the MDL projection)
select location_id, effort_month, refund_rate_pct, effort_tier, total_orders, orders_with_refund, total_refund_amount
from main_marts.rpt_customer_effort_score_proxy
