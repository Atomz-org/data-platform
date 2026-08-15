-- source extract for cmp_mom_growth_by_store (PII columns excluded by the MDL projection)
select location_id, current_month, mom_revenue_growth_pct, mom_order_growth_pct, trailing_3m_avg_revenue, location_name, current_revenue, current_orders, current_customers, prior_month_revenue, prior_month_orders, prior_month_customers, mom_customer_growth_pct
from main_marts.cmp_mom_growth_by_store
