-- source extract for metricflow_time_spine (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    date_day
from main_marts.metricflow_time_spine
