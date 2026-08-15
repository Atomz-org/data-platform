-- source extract for rpt_weekly_business_review (PII columns excluded by the MDL projection)
select week_start, weekly_revenue, revenue_wow_pct, weekly_orders, prev_week_revenue, prev_week_orders, orders_wow_pct, avg_order_value
from main_marts.rpt_weekly_business_review
