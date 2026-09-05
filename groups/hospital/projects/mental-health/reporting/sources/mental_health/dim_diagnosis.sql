-- source extract for dim_diagnosis (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    diagnosis_code,
    diagnosis_label,
    source_vocabulary,
    icd10_group
from main_marts.dim_diagnosis
