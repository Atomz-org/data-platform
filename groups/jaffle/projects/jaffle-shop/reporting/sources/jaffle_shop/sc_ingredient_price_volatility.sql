-- source extract for sc_ingredient_price_volatility (PII columns excluded by the MDL projection)
select ingredient_id, ingredient_name, ingredient_category, price_observations, avg_price, min_price, max_price, price_range, coefficient_of_variation_proxy, volatility_category
from main_marts.sc_ingredient_price_volatility
