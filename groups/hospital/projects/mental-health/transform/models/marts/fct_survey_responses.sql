-- Population survey at DISTINCT-response grain. Upstream publishes 292,364
-- rows of which ~2.3k are exact duplicates; the duplication is an upstream
-- artefact, not signal. The content-hash surrogate key drives the
-- role-generated dedupe in staging, so this mart is already at distinct
-- grain — the raw table keeps the full multiplicity for audit.

select
    response_id,
    content_hash_id as content_hash,
    surveyed_at,
    gender,
    country,
    occupation,
    self_employed,
    family_history,
    sought_treatment,
    case when sought_treatment = 'yes' then 1 else 0 end as is_treatment_seeking,
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
from {{ ref('stg_kaggle_mh__survey_responses') }}
