-- ECG recording features by disorder cohort. Static cohort: no event time
-- exists upstream, so no time axis and no semantic-layer projection.

select
    r.recording_id,
    r.diagnosis_code,
    d.icd10_group,
    r.disorder_group,
    r.n_samples,
    r.n_leads,
    r.signal_mean,
    r.signal_std,
    r.signal_min,
    r.signal_max,
    r.signal_rms,
    r.lead2_mean,
    r.lead2_std
from {{ ref('stg_kaggle_mh__ecg_recordings') }} as r
left join {{ ref('dim_diagnosis') }} as d
    on r.diagnosis_code = d.diagnosis_code
