-- source extract for kpi_loyalty_active_rate (PII columns excluded by the MDL projection)
select txn_month, active_members, total_enrolled, active_rate_pct
from main_marts.kpi_loyalty_active_rate
