-- source extract for fct_commodity_prices_daily (PII columns excluded by the MDL projection)
select price_id, commodity_id, price_date, close_price, high_price, low_price, currency_code, volume, price_change_pct, is_latest, price_basis, quote_unit, open_price, prev_close_price, price_change, moving_avg_20d, moving_avg_50d, high_252d, low_252d
from main_marts.fct_commodity_prices_daily
