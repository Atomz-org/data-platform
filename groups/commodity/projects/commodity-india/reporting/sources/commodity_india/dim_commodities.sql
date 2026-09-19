-- source extract for dim_commodities (PII columns excluded by the MDL projection)
select commodity_id, category, segment, exchange, price_basis, quote_unit, market_unit, current_duty_rate, is_import_prohibited, commodity_name, yahoo_symbol, spot_symbol, has_spot_feed, unit_dimension, current_tariff_id, current_duty_basis
from main_marts.dim_commodities
