-- source extract for fct_treatment_episodes (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    episode_id,
    patient_id,
    diagnosis_code,
    icd10_group,
    treatment_started_at,
    outcome,
    adherence_pct,
    is_improved,
    diagnosis_label,
    age,
    gender,
    symptom_severity,
    mood_score,
    sleep_quality,
    physical_activity_hrs_week,
    medication,
    therapy_type,
    treatment_duration_weeks,
    stress_level,
    treatment_progress,
    emotional_state
from main_marts.fct_treatment_episodes
