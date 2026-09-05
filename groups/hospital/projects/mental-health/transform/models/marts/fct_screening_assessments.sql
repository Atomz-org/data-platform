-- Behavioural screening fact. Static cohort: no event time exists upstream,
-- so this mart carries no time axis and stays out of the semantic layer.

select
    s.assessment_id,
    s.diagnosis_code,
    d.icd10_group,
    s.expert_diagnosis,
    case when s.expert_diagnosis <> 'normal' then 1 else 0 end as is_disorder,
    s.sadness,
    s.euphoric,
    s.exhausted,
    s.sleep_disorder,
    s.mood_swing,
    s.suicidal_thoughts,
    s.anorexia,
    s.authority_respect,
    s.try_explanation,
    s.aggressive_response,
    s.ignore_move_on,
    s.nervous_breakdown,
    s.admit_mistakes,
    s.overthinking,
    s.sexual_activity_score,
    s.concentration_score,
    s.optimism_score
from {{ ref('stg_kaggle_mh__screening_assessments') }} as s
left join {{ ref('dim_diagnosis') }} as d
    on s.diagnosis_code = d.diagnosis_code
