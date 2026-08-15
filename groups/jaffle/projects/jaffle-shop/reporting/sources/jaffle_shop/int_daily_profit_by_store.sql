-- source extract for int_daily_profit_by_store (PII columns excluded by the MDL projection)
select location_id, profit_date, daily_profit, profit_margin_pct, total_revenue, daily_expenses
from main_marts.int_daily_profit_by_store
