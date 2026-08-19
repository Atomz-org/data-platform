-- source extract for rpt_revenue_driver_decomposition (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    location_id,
    revenue_month,
    traffic_change,
    frequency_change,
    ticket_change
from main_marts.rpt_revenue_driver_decomposition
