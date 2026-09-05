-- Case-mix benchmark: this entity's episode mix vs the national in-patient
-- mix, at conformed ICD-10 group grain. The ONLY place patient-level and
-- population-level data meet, and only as shares at group grain — never a
-- patient-level join. Registry side uses the latest fully-published year,
-- counts only ('number'), both sexes, excluding the 'all disorders' total row
-- and suppressed cells.

with hospital as (
    select
        icd10_group,
        count(*) as hospital_episodes
    from {{ ref('fct_treatment_episodes') }}
    where icd10_group is not null
    group by icd10_group
),

registry_latest_year as (
    select max(year) as year
    from {{ ref('fct_registry_annual') }}
    where unit = 'number'
        and sex = 'both sexes'
        and value is not null
),

registry as (
    select
        r.conformed_icd10_group as icd10_group,
        r.year as registry_year,
        sum(r.value) as registry_inpatients
    from {{ ref('fct_registry_annual') }} as r
    inner join registry_latest_year as y on r.year = y.year
    where r.unit = 'number'
        and r.sex = 'both sexes'
        and r.conformed_icd10_group <> 'all disorders'
        and r.value is not null
    group by r.conformed_icd10_group, r.year
)

select
    coalesce(h.icd10_group, r.icd10_group) as icd10_group,
    h.hospital_episodes,
    h.hospital_episodes * 1.0
    / nullif(sum(h.hospital_episodes) over (), 0) as hospital_share,
    r.registry_year,
    r.registry_inpatients,
    r.registry_inpatients * 1.0
    / nullif(sum(r.registry_inpatients) over (), 0) as registry_share
from hospital as h
full outer join registry as r
    on h.icd10_group = r.icd10_group
