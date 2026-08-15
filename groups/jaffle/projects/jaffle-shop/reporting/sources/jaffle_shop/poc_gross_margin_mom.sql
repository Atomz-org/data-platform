-- source extract for poc_gross_margin_mom (PII columns excluded by the MDL projection)
select sale_month, current_margin, prior_month_margin, margin_change_pp, current_revenue, current_cogs
from main_marts.poc_gross_margin_mom
