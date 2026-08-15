-- source extract for cmp_seasonal_yoy (PII columns excluded by the MDL projection)
select location_id, current_fiscal_year, fiscal_quarter, current_revenue, prior_year_revenue, yoy_revenue_growth_pct, location_name, current_orders, prior_year_orders, revenue_change, yoy_order_growth_pct
from main_marts.cmp_seasonal_yoy
