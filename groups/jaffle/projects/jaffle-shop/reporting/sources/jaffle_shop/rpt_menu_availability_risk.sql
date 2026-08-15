-- source extract for rpt_menu_availability_risk (PII columns excluded by the MDL projection)
select product_id, product_name, total_ingredients, unavailable_ingredients, at_risk_ingredients, watch_ingredients, min_ingredient_weeks_supply, menu_availability_status, risk_priority, pct_ingredients_at_risk
from main_marts.rpt_menu_availability_risk
