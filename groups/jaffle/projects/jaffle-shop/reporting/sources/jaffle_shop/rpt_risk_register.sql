-- source extract for rpt_risk_register (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    risk_domain,
    risk_count,
    risk_description
from main_marts.rpt_risk_register
