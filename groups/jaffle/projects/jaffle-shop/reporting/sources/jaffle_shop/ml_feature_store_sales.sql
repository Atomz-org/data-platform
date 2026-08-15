-- source extract for ml_feature_store_sales (PII columns excluded by the MDL projection)
select store_id, month_start, monthly_revenue, trailing_3m_avg_revenue, trailing_6m_avg_revenue, same_month_prior_year, staff_count, store_name, monthly_orders, monthly_customers, active_days_in_month, prior_month_revenue, mom_revenue_growth, month_of_year, labor_cost_pct, total_marketing_spend, operating_margin_pct
from main_marts.ml_feature_store_sales
