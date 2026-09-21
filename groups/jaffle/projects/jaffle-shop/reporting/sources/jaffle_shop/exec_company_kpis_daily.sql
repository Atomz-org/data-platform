-- source extract for exec_company_kpis_daily (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    kpi_date,
    total_revenue,
    total_orders,
    active_customers,
    avg_ticket_size
from main_marts.exec_company_kpis_daily
