-- source extract for poc_email_engagement_mom (PII columns excluded by the MDL projection)
select email_month, current_open_rate, prior_month_open_rate, open_rate_change_pp, current_ctr, prior_month_ctr, current_sent, prior_month_sent
from main_marts.poc_email_engagement_mom
