-- source extract for fct_registry_annual (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    statistic_id,
    year_date,
    unit,
    sex,
    conformed_icd10_group,
    value,
    statistic_code,
    statistic_label,
    year,
    icd10_group_code,
    icd10_group,
    is_suppressed
from main_marts.fct_registry_annual
