-- source extract for rpt_commodity_price_board (PII columns excluded by the MDL projection)
select commodity_id, category, benchmark_price_usd, landed_price_inr, is_stale, commodity_name, segment, exchange, price_basis, quote_unit, price_date, price_change_pct, high_252d, low_252d, market_unit, usd_inr_rate, effective_duty_rate, duty_basis, is_import_prohibited, is_duty_rate_confirmed, landed_price_change_pct, spot_price_usd, spot_quoted_at, futures_spot_basis_pct, price_age_days
from main_marts.rpt_commodity_price_board
