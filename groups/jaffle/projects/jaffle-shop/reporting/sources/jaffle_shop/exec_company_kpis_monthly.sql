-- source extract for exec_company_kpis_monthly (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    month_start,
    monthly_revenue,
    mom_revenue_growth,
    yoy_revenue_growth
from main_marts.exec_company_kpis_monthly
