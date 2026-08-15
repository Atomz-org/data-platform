-- source extract for trend_inventory_turnover (PII columns excluded by the MDL projection)
select week_start, location_id, total_units_on_hand, weekly_movements, turnover_ratio, turnover_4w_ma, prev_week_turnover, turnover_trend
from main_marts.trend_inventory_turnover
