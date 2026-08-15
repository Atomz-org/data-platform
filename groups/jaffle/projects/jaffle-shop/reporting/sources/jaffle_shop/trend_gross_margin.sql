-- source extract for trend_gross_margin (PII columns excluded by the MDL projection)
select sale_date, revenue, cogs, gross_profit, gross_margin_pct, margin_7d_ma, margin_28d_ma, margin_status
from main_marts.trend_gross_margin
