-- source extract for poc_training_completions_mom (PII columns excluded by the MDL projection)
select completion_month, current_completions, prior_month_completions, current_employees, prior_month_employees, completions_mom_pct
from main_marts.poc_training_completions_mom
