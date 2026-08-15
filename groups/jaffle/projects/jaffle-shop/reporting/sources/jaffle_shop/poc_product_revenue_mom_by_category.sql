-- source extract for poc_product_revenue_mom_by_category (PII columns excluded by the MDL projection)
select sale_month, category, current_revenue, prior_month_revenue, current_units, prior_month_units, revenue_mom_pct, units_mom_pct
from main_marts.poc_product_revenue_mom_by_category
