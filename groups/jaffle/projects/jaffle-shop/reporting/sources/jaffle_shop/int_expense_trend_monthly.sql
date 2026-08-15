-- source extract for int_expense_trend_monthly (PII columns excluded by the MDL projection)
select location_id, expense_category_id, category_name, expense_month, total_expense_amount, mom_change_amount, mom_change_pct, rolling_3m_avg_expense, is_operating_expense, is_cost_of_goods_sold, expense_count, avg_expense_amount, prev_month_expense_amount
from main_marts.int_expense_trend_monthly
