-- source extract for int_employee_cross_location (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    employee_id,
    locations_worked,
    location_flexibility
from main_marts.int_employee_cross_location
