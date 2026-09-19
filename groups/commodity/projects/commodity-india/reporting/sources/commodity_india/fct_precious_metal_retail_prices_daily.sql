-- source extract for fct_precious_metal_retail_prices_daily (PII columns excluded by the MDL projection)
select retail_price_id, commodity_id, price_date, purity_code, price_inr_per_gram, price_inr_per_10g, price_inr_per_kg, purity_label, fineness, price_basis, is_duty_rate_confirmed
from main_marts.fct_precious_metal_retail_prices_daily
