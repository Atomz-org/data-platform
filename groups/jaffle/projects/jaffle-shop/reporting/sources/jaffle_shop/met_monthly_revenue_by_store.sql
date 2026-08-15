-- source extract for met_monthly_revenue_by_store (PII columns excluded by the MDL projection)
select month_start, location_id, mom_revenue_growth, yoy_revenue_growth, fiscal_year, fiscal_quarter, store_name, fiscal_month, monthly_revenue, monthly_orders, monthly_gross_revenue, monthly_tax_collected, avg_order_value, active_days, prev_month_revenue, same_month_last_year_revenue
from main_marts.met_monthly_revenue_by_store
