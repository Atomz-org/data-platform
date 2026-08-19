-- source extract for rpt_innovation_pipeline (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    season_name,
    total_units_sold,
    total_revenue
from main_marts.rpt_innovation_pipeline
