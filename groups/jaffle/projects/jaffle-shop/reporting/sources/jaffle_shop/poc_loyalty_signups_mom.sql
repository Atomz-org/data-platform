-- source extract for poc_loyalty_signups_mom (PII columns excluded by the MDL projection)
select enrollment_month, current_signups, prior_month_signups, signups_change, signups_mom_pct
from main_marts.poc_loyalty_signups_mom
