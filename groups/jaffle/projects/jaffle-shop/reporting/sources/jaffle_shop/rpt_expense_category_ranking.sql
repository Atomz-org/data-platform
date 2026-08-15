-- source extract for rpt_expense_category_ranking (PII columns excluded by the MDL projection)
select location_id, location_name, expense_category_id, category_name, is_operating_expense, is_cost_of_goods_sold, expense_month, expense_count, total_spend, avg_spend, store_month_total_spend, spend_share_pct, category_rank
from main_marts.rpt_expense_category_ranking
