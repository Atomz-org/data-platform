-- source extract for fct_ecg_recordings (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    recording_id,
    diagnosis_code,
    disorder_group,
    icd10_group,
    n_samples,
    n_leads,
    signal_mean,
    signal_std,
    signal_min,
    signal_max,
    signal_rms,
    lead2_mean,
    lead2_std
from main_marts.fct_ecg_recordings
