-- source extract for fct_india_landed_prices_daily (PII columns excluded by the MDL projection)
select price_id, commodity_id, price_date, market_unit, usd_inr_rate, tariff_id, effective_duty_rate, is_duty_rate_confirmed, landed_price_inr, duty_inr, price_basis, quote_unit, benchmark_price_usd, benchmark_usd_per_market_unit, usd_inr_fixed_on, duty_basis, is_import_prohibited, assessable_value_inr, landed_price_change_inr, landed_price_change_pct
from main_marts.fct_india_landed_prices_daily
