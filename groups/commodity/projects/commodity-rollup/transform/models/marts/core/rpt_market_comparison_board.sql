-- Grain: one commodity per market. The latest landed price in every market on
-- the benchmark's footing, the cheapest market to land it in, and how stale
-- each market's number is. The table behind the market comparison board.
with latest as (
    select *
    from {{ ref('fct_landed_prices_daily') }}
    qualify row_number() over (partition by commodity_id, market_code order by price_date desc) = 1
),

cheapest as (
    select commodity_id, cheapest_market_code, cheapest_landed_usd, markets_compared
    from {{ ref('fct_market_spreads_daily') }}
    qualify row_number() over (partition by commodity_id order by price_date desc, market_code) = 1
),

commodities as (
    select * from {{ ref('dim_commodities') }}
),

markets as (
    select * from {{ ref('dim_markets') }}
)

select
    l.market_code || ':' || l.commodity_id                                  as board_row_id,
    l.market_code,
    m.market_name,
    l.currency_code,
    l.commodity_id,
    c.commodity_name,
    c.category,
    c.segment,
    l.price_date,
    l.price_basis,
    l.benchmark_price_usd,
    l.quote_unit,
    l.landed_price_local,
    l.market_unit,
    l.usd_fx_rate,
    l.effective_duty_rate,
    l.is_import_prohibited,
    l.is_duty_rate_confirmed,
    l.landed_price_usd_per_quote_unit,
    l.import_parity_premium_pct,
    ch.cheapest_market_code,
    ch.cheapest_landed_usd,
    ch.markets_compared,
    l.market_code = ch.cheapest_market_code                                 as is_cheapest_market,
    round({{ sf_safe_divide('l.landed_price_usd_per_quote_unit - ch.cheapest_landed_usd', 'ch.cheapest_landed_usd') }}, 6)
                                                                            as spread_to_cheapest_pct,
    {{ sf_datediff('day', 'l.price_date', 'current_date') }}                as price_age_days,
    {{ sf_datediff('day', 'l.price_date', 'current_date') }} > 4            as is_stale
from latest as l
inner join commodities as c on c.commodity_id = l.commodity_id
inner join markets as m on m.market_code = l.market_code
left join cheapest as ch on ch.commodity_id = l.commodity_id
