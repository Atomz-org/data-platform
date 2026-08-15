-- source extract for trend_gift_card_sales (PII columns excluded by the MDL projection)
select activation_date, cards_activated, total_loaded, cards_7d_ma, loaded_7d_ma, cards_28d_total, loaded_28d_total, cards_same_day_last_week
from main_marts.trend_gift_card_sales
