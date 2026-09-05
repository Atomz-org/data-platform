-- Conformed diagnosis dimension: every source vocabulary's label mapped onto
-- the ICD-10 diagnostic groups used by the national registry. The only
-- sanctioned bridge between patient-level facts and population benchmarks.
-- icd10_group is lower-cased to match role-cleaned staging output.

select
    diagnosis_code,
    diagnosis_label,
    source_vocabulary,
    lower(trim(icd10_group)) as icd10_group
from {{ ref('diagnosis_map') }}
