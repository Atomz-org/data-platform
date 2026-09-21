-- Grain: one market. The registry row beside what the roll-up has actually
-- received from that market's sister: a market with no prices is registered
-- but not reporting, and the board should say which.
with markets as (
    select * from {{ ref('markets') }}
),

reported as (
    select
        market_code,
        min(price_date)                                     as first_price_date,
        max(price_date)                                     as latest_price_date,
        count(distinct commodity_id)                        as commodities_priced,
        count(*)                                            as landed_price_rows
    from {{ ref('stg_sisters__landed_prices') }}
    group by market_code
)

select
    m.market_code,
    m.market_name,
    m.country_code,
    m.currency_code,
    m.home_exchange,
    m.timezone,
    m.project,
    r.market_code is not null                               as is_reporting,
    r.first_price_date,
    r.latest_price_date,
    coalesce(r.commodities_priced, 0)                       as commodities_priced,
    coalesce(r.landed_price_rows, 0)                        as landed_price_rows
from markets as m
left join reported as r on r.market_code = m.market_code
