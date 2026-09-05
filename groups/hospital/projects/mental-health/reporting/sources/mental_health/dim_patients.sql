-- source extract for dim_patients (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    patient_id,
    age,
    gender,
    first_treatment_started_at,
    episode_count
from main_marts.dim_patients
