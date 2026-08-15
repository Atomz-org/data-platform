-- source extract for rpt_ingredient_price_watch (PII columns excluded by the MDL projection)
select ingredient_id, ingredient_name, ingredient_category, is_perishable, price_month, avg_unit_cost, min_unit_cost, max_unit_cost, prev_month_avg_cost, mom_cost_change_pct, price_record_count, price_trend_status, requires_attention
from main_marts.rpt_ingredient_price_watch
