-- source extract for poc_refund_rate_mom (PII columns excluded by the MDL projection)
select metric_month, current_rate, prior_month_rate, rate_change_pp, current_refunds, prior_month_refunds
from main_marts.poc_refund_rate_mom
