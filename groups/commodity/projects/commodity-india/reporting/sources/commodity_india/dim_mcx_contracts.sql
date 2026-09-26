-- source extract for dim_mcx_contracts (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    contract_id,
    contract_code,
    mcx_commodity,
    commodity_id,
    expiry_date,
    contract_kind,
    is_open,
    contract_name,
    segment,
    is_flagship,
    instrument_type,
    exchange,
    days_to_expiry,
    is_traded_today,
    lot_size,
    lot_unit,
    quote_size,
    quote_unit
from main_marts.dim_mcx_contracts
