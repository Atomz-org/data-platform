-- source extract for hr_shift_preference_fulfillment (PII columns excluded by the MDL projection)
select employee_id, total_shifts, matched_shifts, fulfillment_pct
from main_marts.hr_shift_preference_fulfillment
