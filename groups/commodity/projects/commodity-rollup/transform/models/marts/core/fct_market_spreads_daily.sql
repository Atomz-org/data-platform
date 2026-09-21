-- Grain: one commodity per market per price date, on days at least two markets
-- priced it. Where is a commodity cheapest to land today, and by how much does
-- each other market pay over that? Spreads are between landed prices on the
-- same benchmark footing (USD per quote unit), so they are pure market effects.
with comparable as (
    select *
    from {{ ref('fct_landed_prices_daily') }}
    where landed_price_usd_per_quote_unit is not null
),

ranked as (
    select
        *,
        count(*) over (partition by commodity_id, price_date)                as markets_compared,
        min(landed_price_usd_per_quote_unit) over (partition by commodity_id, price_date)
                                                                            as cheapest_landed_usd,
        first_value(market_code) over (
            partition by commodity_id, price_date
            order by landed_price_usd_per_quote_unit, market_code)          as cheapest_market_code
    from comparable
)

select
    landed_price_id,
    market_code,
    commodity_id,
    price_date,
    quote_unit,
    markets_compared,
    landed_price_usd_per_quote_unit,
    cheapest_market_code,
    cheapest_landed_usd,
    market_code = cheapest_market_code                                      as is_cheapest_market,
    cast(round(landed_price_usd_per_quote_unit - cheapest_landed_usd, 6) as decimal(18, 6))
                                                                            as spread_to_cheapest_usd,
    round({{ sf_safe_divide('landed_price_usd_per_quote_unit - cheapest_landed_usd', 'cheapest_landed_usd') }}, 6)
                                                                            as spread_to_cheapest_pct
from ranked
where markets_compared >= 2
