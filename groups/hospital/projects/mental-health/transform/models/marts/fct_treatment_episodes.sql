-- Treatment episode fact, enriched with the conformed diagnosis group.

select
    e.episode_id,
    e.patient_id,
    e.diagnosis_code,
    d.diagnosis_label,
    d.icd10_group,
    e.age,
    e.gender,
    e.symptom_severity,
    e.mood_score,
    e.sleep_quality,
    e.physical_activity_hrs_week,
    e.medication,
    e.therapy_type,
    e.treatment_started_at,
    e.treatment_duration_weeks,
    e.stress_level,
    e.outcome,
    e.treatment_progress,
    e.emotional_state,
    e.adherence_pct,
    case when e.outcome = 'improved' then 1 else 0 end as is_improved
from {{ ref('stg_kaggle_mh__treatment_episodes') }} as e
left join {{ ref('dim_diagnosis') }} as d
    on e.diagnosis_code = d.diagnosis_code
