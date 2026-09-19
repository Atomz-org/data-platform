-- source extract for int_store_hours_compliance (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    location_id,
    work_date,
    compliance_status
from main_marts.int_store_hours_compliance
