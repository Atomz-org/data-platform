-- source extract for trend_expense_daily (PII columns excluded by the MDL projection)
select incurred_date, location_id, total_expenses, expense_count, expense_7d_ma, expense_28d_ma, expense_anomaly
from main_marts.trend_expense_daily
