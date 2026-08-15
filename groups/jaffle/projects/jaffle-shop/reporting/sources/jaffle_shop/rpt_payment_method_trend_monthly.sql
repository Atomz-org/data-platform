-- source extract for rpt_payment_method_trend_monthly (PII columns excluded by the MDL projection)
select report_month, location_id, payment_method, order_count, transaction_count, method_total, completed_amount, failed_amount, location_month_total, revenue_share_pct, prev_month_total, mom_growth_rate
from main_marts.rpt_payment_method_trend_monthly
