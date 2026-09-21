-- source extract for rpt_market_comparison_board (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    board_row_id,
    market_code,
    commodity_id,
    category,
    landed_price_usd_per_quote_unit,
    spread_to_cheapest_pct,
    is_stale,
    market_name,
    currency_code,
    commodity_name,
    segment,
    price_date,
    price_basis,
    benchmark_price_usd,
    quote_unit,
    landed_price_local,
    market_unit,
    usd_fx_rate,
    effective_duty_rate,
    is_import_prohibited,
    is_duty_rate_confirmed,
    import_parity_premium_pct,
    cheapest_market_code,
    cheapest_landed_usd,
    markets_compared,
    is_cheapest_market,
    price_age_days
from main_marts.rpt_market_comparison_board
