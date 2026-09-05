-- National benchmark fact at published grain: statistic x year x sex x
-- ICD-10 diagnostic group. NULL value = suppressed or not-applicable cell —
-- never zero-fill, never coalesce. conformed_icd10_group folds the registry's
-- legacy classification labels into the modern group so case-mix joins hold
-- across the 2001-2023 span.

select
    statistic_id,
    statistic_code,
    statistic_label,
    year,
    year_date,
    sex,
    icd10_group_code,
    icd10_group,
    case
        when icd10_group = 'schizophrenia'
            then 'schizophrenia, schizotypal and delusional disorders'
        when icd10_group = 'organic category'
            then 'organic mental disorders'
        when icd10_group = 'mental handicap'
            then 'intellectual disability'
        else icd10_group
    end as conformed_icd10_group,
    unit,
    value,
    value is null as is_suppressed
from {{ ref('stg_kaggle_mh__registry_annual') }}
