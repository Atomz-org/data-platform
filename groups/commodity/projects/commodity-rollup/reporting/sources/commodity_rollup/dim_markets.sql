-- source extract for dim_markets (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    market_code,
    country_code,
    currency_code,
    is_reporting,
    latest_price_date,
    market_name,
    home_exchange,
    timezone,
    project,
    first_price_date,
    commodities_priced,
    landed_price_rows
from main_marts.dim_markets
