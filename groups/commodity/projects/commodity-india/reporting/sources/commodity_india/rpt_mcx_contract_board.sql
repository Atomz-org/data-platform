-- source extract for rpt_mcx_contract_board (PII columns excluded by the MDL projection)
select contract_code, commodity_id, quote_equivalent_inr, lot_value_inr, is_stale, exchange, contract_name, price_date, price_basis, is_duty_rate_confirmed, quote_size, quote_unit, lot_size, lot_unit, price_age_days
from main_marts.rpt_mcx_contract_board
