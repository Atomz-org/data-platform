-- source extract for kpi_profit_margin_by_store (PII columns excluded by the MDL projection)
select month_start, location_id, monthly_revenue, operating_profit, profit_margin_pct
from main_marts.kpi_profit_margin_by_store
