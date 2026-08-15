-- source extract for kpi_refund_rate (PII columns excluded by the MDL projection)
select order_month, total_orders, refunds, refund_rate_pct, refund_value_rate_pct
from main_marts.kpi_refund_rate
