-- source extract for exec_financial_summary_monthly (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    month_start,
    total_revenue,
    gross_profit,
    gross_margin_pct,
    net_profit,
    net_profit_margin_pct
from main_marts.exec_financial_summary_monthly
