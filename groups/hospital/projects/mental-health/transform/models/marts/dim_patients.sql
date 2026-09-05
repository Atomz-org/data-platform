-- Patient dimension derived from treatment episodes (the upstream snapshot
-- carries exactly one episode per patient; the aggregation keeps the model
-- correct if a refresh ever brings more).

select
    patient_id,
    max(age) as age,
    max(gender) as gender,
    min(treatment_started_at) as first_treatment_started_at,
    count(*) as episode_count
from {{ ref('stg_kaggle_mh__treatment_episodes') }}
group by patient_id
