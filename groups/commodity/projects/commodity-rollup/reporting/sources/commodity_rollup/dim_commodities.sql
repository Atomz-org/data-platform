-- source extract for dim_commodities (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    commodity_id,
    category,
    price_basis,
    quote_unit,
    markets_pricing,
    commodity_name,
    segment,
    exchange,
    unit_dimension
from main_marts.dim_commodities
