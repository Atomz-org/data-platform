-- source extract for dq_shift_overlap_check (PII columns excluded by the MDL projection)
select shift_id_1, shift_id_2, employee_id, shift_date, location_1, location_2, start_1, end_1, start_2, end_2, status_1, status_2
from main_marts.dq_shift_overlap_check
