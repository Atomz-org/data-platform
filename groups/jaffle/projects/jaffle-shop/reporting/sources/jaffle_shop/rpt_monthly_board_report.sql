-- source extract for rpt_monthly_board_report (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    month_start,
    total_monthly_revenue,
    revenue_yoy_growth_pct
from main_marts.rpt_monthly_board_report
