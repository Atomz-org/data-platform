-- source extract for poc_marketing_spend_mom (PII columns excluded by the MDL projection)
select month_start, current_spend, prior_month_spend, current_campaigns, prior_month_campaigns, spend_mom_pct, avg_spend_per_campaign
from main_marts.poc_marketing_spend_mom
