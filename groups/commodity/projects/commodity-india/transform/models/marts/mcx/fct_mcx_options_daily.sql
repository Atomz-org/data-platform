-- Grain: one MCX option chain (contract code × option expiry) per trading day.
--
-- MCX options are options on futures: a chain devolves into the first futures
-- contract of the same code expiring on or after it, and that future is what
-- "the underlying" means here — not the most-active series, which may already
-- be a month further out. Max pain and the OI walls are read against it.
with chains as (
    select * from {{ ref('int_mcx__options_chain_daily') }}
),

futures as (
    select contract_code, trade_date, expiry_date, close_price
    from {{ ref('int_mcx__futures_sessions') }}
),

underlying as (
    select
        ch.chain_day_id,
        f.expiry_date                                                   as underlying_expiry_date,
        f.close_price                                                   as underlying_close_price,
        row_number() over (partition by ch.chain_day_id order by f.expiry_date) as rn
    from chains as ch
    inner join futures as f
        on f.contract_code = ch.contract_code
       and f.trade_date = ch.trade_date
       and f.expiry_date >= ch.expiry_date
),

products as (
    select contract_code, mcx_commodity, commodity_id, is_flagship from {{ ref('mcx_products') }}
)

select
    ch.chain_day_id,
    ch.contract_id,
    ch.contract_code,
    p.mcx_commodity,
    p.commodity_id,
    p.is_flagship,
    ch.trade_date,
    ch.expiry_date,
    ch.days_to_expiry,
    row_number() over (partition by ch.contract_code, ch.trade_date order by ch.expiry_date) as expiry_rank,
    max(ch.trade_date) over (partition by ch.contract_code) = ch.trade_date as is_latest,
    ch.strikes_listed,
    ch.call_open_interest_lots,
    ch.put_open_interest_lots,
    ch.call_volume_lots,
    ch.put_volume_lots,
    ch.premium_turnover_inr,
    ch.notional_turnover_inr,
    ch.put_call_ratio_oi,
    ch.put_call_ratio_volume,
    case
        when ch.put_call_ratio_oi is null then null
        when ch.put_call_ratio_oi >= 1.3 then 'put_heavy'
        when ch.put_call_ratio_oi <= 0.7 then 'call_heavy'
        else 'balanced'
    end                                                                 as positioning,
    ch.call_wall_strike,
    ch.put_wall_strike,
    ch.max_pain_strike,
    u.underlying_expiry_date,
    u.underlying_close_price,
    {{ sf_safe_divide('ch.max_pain_strike', 'u.underlying_close_price') }} - 1 as max_pain_distance_pct,
    {{ sf_safe_divide('ch.call_wall_strike', 'u.underlying_close_price') }} - 1 as call_wall_distance_pct,
    {{ sf_safe_divide('ch.put_wall_strike', 'u.underlying_close_price') }} - 1 as put_wall_distance_pct
from chains as ch
inner join products as p on p.contract_code = ch.contract_code
left join underlying as u on u.chain_day_id = ch.chain_day_id and u.rn = 1
