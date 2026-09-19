-- source extract for exec_regional_summary (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    location_id,
    store_name,
    pnl_total_revenue,
    net_profit_margin_pct
from main_marts.exec_regional_summary
