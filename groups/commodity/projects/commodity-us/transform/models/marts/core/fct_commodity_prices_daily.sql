-- Grain: one commodity per price date. USD per quote unit — never compare two
-- commodities' prices directly; their units differ. Indicative commodities have
-- one row per as-of date rather than a daily series.
with prices as (
    select * from {{ ref('int_commodity_prices__usd') }}
),

windowed as (
    select
        *,
        lag(close_price) over (partition by commodity_id order by price_date)    as prev_close_price,
        count(*) over (
            partition by commodity_id order by price_date
            rows between 19 preceding and current row)                            as obs_20d,
        avg(close_price) over (
            partition by commodity_id order by price_date
            rows between 19 preceding and current row)                            as avg_close_20d,
        count(*) over (
            partition by commodity_id order by price_date
            rows between 49 preceding and current row)                            as obs_50d,
        avg(close_price) over (
            partition by commodity_id order by price_date
            rows between 49 preceding and current row)                            as avg_close_50d,
        max(coalesce(high_price, close_price)) over (
            partition by commodity_id order by price_date
            rows between 251 preceding and current row)                           as high_252d,
        min(coalesce(low_price, close_price)) over (
            partition by commodity_id order by price_date
            rows between 251 preceding and current row)                           as low_252d,
        row_number() over (partition by commodity_id order by price_date desc)   as recency_rank
    from prices
)

select
    price_id,
    commodity_id,
    price_date,
    price_basis,
    quote_unit,
    currency_code,
    open_price,
    high_price,
    low_price,
    close_price,
    volume,
    prev_close_price,
    close_price - prev_close_price                                  as price_change,
    {{ sf_safe_divide('close_price - prev_close_price', 'prev_close_price') }} as price_change_pct,
    case when obs_20d = 20 then avg_close_20d end                   as moving_avg_20d,
    case when obs_50d = 50 then avg_close_50d end                   as moving_avg_50d,
    high_252d,
    low_252d,
    recency_rank = 1                                                as is_latest
from windowed
