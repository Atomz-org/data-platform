-- source extract for fct_screening_assessments (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    assessment_id,
    diagnosis_code,
    expert_diagnosis,
    icd10_group,
    is_disorder,
    sadness,
    euphoric,
    exhausted,
    sleep_disorder,
    mood_swing,
    suicidal_thoughts,
    anorexia,
    authority_respect,
    try_explanation,
    aggressive_response,
    ignore_move_on,
    nervous_breakdown,
    admit_mistakes,
    overthinking,
    sexual_activity_score,
    concentration_score,
    optimism_score
from main_marts.fct_screening_assessments
