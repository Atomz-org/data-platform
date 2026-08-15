-- source extract for rpt_quarterly_strategic_review (PII columns excluded by the MDL projection)
select quarter_start, quarterly_revenue, revenue_yoy_pct, quarterly_orders, avg_monthly_revenue, quarterly_revenue_last_year, quarterly_orders_last_year, avg_order_value
from main_marts.rpt_quarterly_strategic_review
