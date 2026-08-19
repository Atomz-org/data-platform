-- source extract for coh_store_vintage_analysis (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    opening_year,
    months_since_opening,
    stores_in_vintage,
    avg_revenue_per_store
from main_marts.coh_store_vintage_analysis
