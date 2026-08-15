-- source extract for poc_gross_margin_yoy (PII columns excluded by the MDL projection)
select sale_month, current_margin, prior_year_margin, margin_yoy_change_pp
from main_marts.poc_gross_margin_yoy
