-- source extract for hr_shift_swap_opportunity (PII columns excluded by the MDL projection)
select location_id, shift_date, swap_opportunities, unique_employees_available
from main_marts.hr_shift_swap_opportunity
