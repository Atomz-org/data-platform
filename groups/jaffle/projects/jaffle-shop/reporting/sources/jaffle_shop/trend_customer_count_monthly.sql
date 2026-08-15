-- source extract for trend_customer_count_monthly (PII columns excluded by the MDL projection)
select month_start, tracked_active_customers, new_customers, customers_3m_ma, prev_month_customers, mom_growth_pct, quarterly_trend
from main_marts.trend_customer_count_monthly
