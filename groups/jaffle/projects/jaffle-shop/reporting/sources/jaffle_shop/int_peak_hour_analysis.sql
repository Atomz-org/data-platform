-- source extract for int_peak_hour_analysis (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    store_id,
    order_hour,
    hour_classification,
    store_total_peak_hours
from main_marts.int_peak_hour_analysis
