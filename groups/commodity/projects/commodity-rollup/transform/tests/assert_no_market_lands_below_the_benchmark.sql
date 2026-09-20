-- Landed = benchmark × (1 + duty) at the sister's own FX, undone here at the
-- same rate, so a landed price below its benchmark is a unit or FX fault in a
-- sister, not a market. A tolerance covers rounding at four decimals.
select landed_price_id, market_code, commodity_id, benchmark_price_usd, landed_price_usd_per_quote_unit
from {{ ref('fct_landed_prices_daily') }}
where landed_price_usd_per_quote_unit < benchmark_price_usd * 0.9999
