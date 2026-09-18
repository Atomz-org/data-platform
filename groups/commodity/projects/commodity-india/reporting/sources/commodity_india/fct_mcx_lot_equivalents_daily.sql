-- source extract for fct_mcx_lot_equivalents_daily (PII columns excluded by the MDL projection)
select lot_equivalent_id, contract_code, commodity_id, price_date, price_basis, quote_unit, quote_equivalent_inr, lot_value_inr, exchange, contract_name, market_unit, is_duty_rate_confirmed, quote_size, lot_size, lot_unit
from main_marts.fct_mcx_lot_equivalents_daily
