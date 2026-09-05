-- source extract for fct_survey_responses (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    response_id,
    content_hash,
    surveyed_at,
    country,
    sought_treatment,
    is_treatment_seeking,
    gender,
    occupation,
    self_employed,
    family_history,
    days_indoors,
    growing_stress,
    changes_habits,
    mental_health_history,
    mood_swings,
    coping_struggles,
    work_interest,
    social_weakness,
    mental_health_interview,
    care_options
from main_marts.fct_survey_responses
