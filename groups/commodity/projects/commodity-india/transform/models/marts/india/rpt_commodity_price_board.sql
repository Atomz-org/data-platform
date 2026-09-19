-- Grain: one tracked commodity. The tracker's dashboard as a table: the latest
-- benchmark, its move, the landed ₹ price, and how old each number is.
with commodities as (
    select * from {{ ref('dim_commodities') }}
),

latest_price as (
    select * from {{ ref('fct_commodity_prices_daily') }}
    where is_latest
),

latest_landed as (
    select *
    from {{ ref('fct_india_landed_prices_daily') }}
    qualify row_number() over (partition by commodity_id order by price_date desc) = 1
),

latest_spot as (
    select
        commodity_id,
        {{ to_major_currency('spot_price', 'currency_code') }}              as spot_price_usd,
        quoted_at
    from {{ ref('stg_gold_api__spot_prices') }}
    qualify row_number() over (partition by commodity_id order by quoted_at desc) = 1
)

select
    c.commodity_id,
    c.commodity_name,
    c.category,
    c.segment,
    c.exchange,
    c.price_basis,
    c.quote_unit,
    p.price_date,
    p.close_price                                                           as benchmark_price_usd,
    p.price_change_pct,
    p.high_252d,
    p.low_252d,
    c.market_unit,
    l.usd_inr_rate,
    l.effective_duty_rate,
    l.duty_basis,
    c.is_import_prohibited,
    l.is_duty_rate_confirmed,
    l.landed_price_inr,
    l.landed_price_change_pct,
    s.spot_price_usd,
    s.quoted_at                                                             as spot_quoted_at,
    {{ sf_safe_divide('p.close_price - s.spot_price_usd', 's.spot_price_usd') }} as futures_spot_basis_pct,
    {{ sf_datediff('day', 'p.price_date', 'current_date') }}                as price_age_days,
    {{ sf_datediff('day', 'p.price_date', 'current_date') }} > 4            as is_stale
from commodities as c
left join latest_price as p on p.commodity_id = c.commodity_id
left join latest_landed as l on l.commodity_id = c.commodity_id
left join latest_spot as s on s.commodity_id = c.commodity_id
