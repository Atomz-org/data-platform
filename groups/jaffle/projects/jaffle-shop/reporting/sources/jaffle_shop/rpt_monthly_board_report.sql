-- source extract for rpt_monthly_board_report (PII columns excluded by the MDL projection)
select month_start, total_monthly_revenue, revenue_yoy_growth_pct, total_monthly_orders, tracked_active_customers, revenue_last_year, avg_order_value
from main_marts.rpt_monthly_board_report
