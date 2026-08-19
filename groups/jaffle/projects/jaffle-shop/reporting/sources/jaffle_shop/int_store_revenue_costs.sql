-- source extract for int_store_revenue_costs (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    store_id,
    report_month,
    net_operating_income,
    operating_margin_pct
from main_marts.int_store_revenue_costs
