-- source extract for rpt_store_opening_playbook (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    store_id,
    avg_monthly_revenue_first_6m
from main_marts.rpt_store_opening_playbook
