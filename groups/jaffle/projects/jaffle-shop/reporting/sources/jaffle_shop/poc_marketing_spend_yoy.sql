-- source extract for poc_marketing_spend_yoy (PII columns excluded by the MDL projection)
select month_start, current_spend, prior_year_spend, spend_yoy_pct
from main_marts.poc_marketing_spend_yoy
