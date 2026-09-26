{{ config(materialized='table') }}
-- Grain: one MCX option chain (contract code × expiry) per trading day.
--
-- What a desk reads off an option chain, summarised to one row:
--   * put/call ratio by open interest and by volume — positioning and flow;
--   * the OI walls: the call strike with most open interest (where writers are
--     defending an upside cap) and the put strike with most (the floor);
--   * max pain — the settlement strike at which option holders, in aggregate,
--     would be paid least. It is where the chain's writers are best off, not a
--     forecast, and near expiry the underlying is often pulled toward it.
--
-- Turnover: MCX's option `Value` is *notional* — (strike + premium) × quantity,
-- verified per row: turnover ÷ (lots × quote bases per lot) lands at strike plus
-- the premium. The premium actually paid is therefore Value − strike × lots ×
-- quote bases per lot, which is what `premium_turnover_inr` holds; the notional
-- is kept, named as what it is. Reading Value as premium overstated option
-- activity about forty-fold.
--
-- Max pain is evaluated over strikes that carry open interest, one self-join
-- per chain-day (hundreds of strikes, not thousands). Lot size is constant
-- inside a chain, so pain is in lots × ₹ per quote basis and only its argmin
-- is used.
with options as (
    select
        o.contract_id,
        o.contract_code,
        cast(o.traded_at as date)                                           as trade_date,
        cast(o.expiry_date as date)                                         as expiry_date,
        o.strike_price,
        o.option_type,
        o.open_interest_lots,
        o.volume_lots,
        o.turnover_lakhs * 100000                                           as notional_turnover_inr,
        o.turnover_lakhs * 100000
            - o.strike_price * o.volume_lots * p.quote_units_per_lot        as premium_turnover_inr,
        o.close_price
    from {{ ref('stg_mcx__options_bhavcopy') }} as o
    inner join {{ ref('mcx_products') }} as p on p.contract_code = o.contract_code
    where o.strike_price > 0
),

sides as (
    select
        contract_id,
        contract_code,
        trade_date,
        expiry_date,
        count(distinct strike_price)                                        as strikes_listed,
        sum(case when option_type = 'ce' then open_interest_lots else 0 end) as call_open_interest_lots,
        sum(case when option_type = 'pe' then open_interest_lots else 0 end) as put_open_interest_lots,
        sum(case when option_type = 'ce' then volume_lots else 0 end)        as call_volume_lots,
        sum(case when option_type = 'pe' then volume_lots else 0 end)        as put_volume_lots,
        sum(premium_turnover_inr)                                           as premium_turnover_inr,
        sum(notional_turnover_inr)                                          as notional_turnover_inr
    from options
    group by contract_id, contract_code, trade_date, expiry_date
),

walls as (
    select
        contract_id,
        trade_date,
        option_type,
        strike_price,
        row_number() over (
            partition by contract_id, trade_date, option_type
            order by open_interest_lots desc, strike_price
        )                                                                   as oi_rank
    from options
    where open_interest_lots > 0
),

candidates as (
    select distinct contract_id, trade_date, strike_price as settle_at
    from options
    where open_interest_lots > 0
),

pain as (
    select
        c.contract_id,
        c.trade_date,
        c.settle_at,
        sum(case
                when o.option_type = 'ce' then o.open_interest_lots * greatest(c.settle_at - o.strike_price, 0)
                else o.open_interest_lots * greatest(o.strike_price - c.settle_at, 0)
            end)                                                            as holder_payout
    from candidates as c
    inner join options as o
        on o.contract_id = c.contract_id and o.trade_date = c.trade_date
       and o.open_interest_lots > 0
    group by c.contract_id, c.trade_date, c.settle_at
),

max_pain as (
    select contract_id, trade_date, settle_at as max_pain_strike
    from (
        select
            *,
            row_number() over (partition by contract_id, trade_date order by holder_payout, settle_at) as rn
        from pain
    ) as ranked
    where rn = 1
)

select
    s.contract_id || ':' || cast(s.trade_date as varchar)                  as chain_day_id,
    s.contract_id,
    s.contract_code,
    s.trade_date,
    s.expiry_date,
    {{ sf_datediff('day', 's.trade_date', 's.expiry_date') }}              as days_to_expiry,
    s.strikes_listed,
    s.call_open_interest_lots,
    s.put_open_interest_lots,
    s.call_volume_lots,
    s.put_volume_lots,
    s.premium_turnover_inr,
    s.notional_turnover_inr,
    {{ sf_safe_divide('s.put_open_interest_lots', 's.call_open_interest_lots') }} as put_call_ratio_oi,
    {{ sf_safe_divide('s.put_volume_lots', 's.call_volume_lots') }}               as put_call_ratio_volume,
    cw.strike_price                                                         as call_wall_strike,
    pw.strike_price                                                         as put_wall_strike,
    mp.max_pain_strike
from sides as s
left join walls as cw
    on cw.contract_id = s.contract_id and cw.trade_date = s.trade_date
   and cw.option_type = 'ce' and cw.oi_rank = 1
left join walls as pw
    on pw.contract_id = s.contract_id and pw.trade_date = s.trade_date
   and pw.option_type = 'pe' and pw.oi_rank = 1
left join max_pain as mp
    on mp.contract_id = s.contract_id and mp.trade_date = s.trade_date
