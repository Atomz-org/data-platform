-- source extract for poc_gift_card_sales_mom (PII columns excluded by the MDL projection)
select activation_month, current_cards, prior_month_cards, current_value, prior_month_value, cards_mom_pct, value_mom_pct
from main_marts.poc_gift_card_sales_mom
