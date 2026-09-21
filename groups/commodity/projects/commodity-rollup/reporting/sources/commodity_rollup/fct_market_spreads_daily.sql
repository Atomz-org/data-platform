-- source extract for fct_market_spreads_daily (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    landed_price_id,
    market_code,
    commodity_id,
    price_date,
    cheapest_market_code,
    spread_to_cheapest_usd,
    spread_to_cheapest_pct,
    is_cheapest_market,
    quote_unit,
    markets_compared,
    landed_price_usd_per_quote_unit,
    cheapest_landed_usd
from main_marts.fct_market_spreads_daily
