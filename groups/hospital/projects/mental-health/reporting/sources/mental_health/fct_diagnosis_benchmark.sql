-- source extract for fct_diagnosis_benchmark (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    icd10_group,
    hospital_episodes,
    hospital_share,
    registry_inpatients,
    registry_share,
    registry_year
from main_marts.fct_diagnosis_benchmark
