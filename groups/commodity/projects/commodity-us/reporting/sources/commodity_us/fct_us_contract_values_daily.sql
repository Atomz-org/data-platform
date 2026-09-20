-- source extract for fct_us_contract_values_daily (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    contract_value_id,
    contract_code,
    exchange,
    commodity_id,
    price_date,
    price_basis,
    quote_unit,
    quote_equivalent_usd,
    lot_value_usd,
    contract_name,
    market_unit,
    effective_duty_rate,
    is_duty_rate_confirmed,
    quote_size,
    lot_size,
    lot_unit
from main_marts.fct_us_contract_values_daily
