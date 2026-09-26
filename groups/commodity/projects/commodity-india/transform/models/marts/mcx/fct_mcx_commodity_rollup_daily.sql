-- Grain: one MCX commodity per trading day — gold, not GOLD + GOLDM + GOLDPETAL.
-- The fact the per-commodity semantic model (`mcx_commodities`) is built on.
--
-- Two different questions, answered from two different places:
--
--   * **What the commodity's price did** — return, variance, momentum, trend,
--     curve, parity — is read from the *flagship* contract (`is_flagship` in
--     `mcx_products`: GOLD, SILVER, CRUDEOIL, ...). The minis track the same
--     underlying; averaging GOLD's return with GOLDPETAL's counts one market
--     twice and blends two liquidity profiles into a number nobody traded.
--
--   * **How much of it traded, and how it is positioned** — turnover, open
--     interest, options — is summed across *every* code and expiry, in rupees.
--     Lots are not additive across codes (a GOLD lot is 1 kg, a GOLDPETAL lot
--     1 g), so volume is restated in flagship-lot equivalents (turnover ÷ the
--     flagship's notional per lot) and option open interest is weighted by its
--     underlying's notional per lot before the put/call ratio is taken.
--
-- Every measure the semantic layer aggregates is a per-day sum, count or
-- per-day stock; nothing here is a rolling average a page would average again.
with codes as (
    select * from {{ ref('fct_mcx_commodity_daily') }}
),

flagship as (
    select * from codes where is_flagship
),

activity as (
    -- Across all codes and every open expiry of each code.
    select
        mcx_commodity,
        trade_date,
        count(*)                                                        as codes_trading,
        sum(turnover_inr)                                               as turnover_inr,
        sum(case when not is_flagship then turnover_inr else 0 end)     as mini_turnover_inr,
        sum(open_interest_value_inr)                                    as open_interest_value_inr
    from codes
    group by mcx_commodity, trade_date
),

-- Where the flagship has no landed-parity row (GOLD: only GOLDM is sized in
-- `mcx_contract_lots`), the commodity's parity premium is read from the code
-- that has one. A premium is unit-free, so any code of the commodity says it.
parity as (
    select mcx_commodity, trade_date, premium_to_landed_pct
    from (
        select
            mcx_commodity, trade_date, premium_to_landed_pct,
            row_number() over (partition by mcx_commodity, trade_date
                               order by is_flagship desc, contract_code) as rn
        from codes
        where premium_to_landed_pct is not null
    ) as ranked
    where rn = 1
),

options as (
    select
        o.mcx_commodity,
        o.trade_date,
        sum(o.put_open_interest_lots * o.underlying_close_price * p.quote_units_per_lot)  as put_oi_notional_inr,
        sum(o.call_open_interest_lots * o.underlying_close_price * p.quote_units_per_lot) as call_oi_notional_inr,
        sum(o.premium_turnover_inr)                                                        as option_premium_turnover_inr,
        sum(o.notional_turnover_inr)                                                       as option_notional_turnover_inr
    from {{ ref('fct_mcx_options_daily') }} as o
    inner join {{ ref('mcx_products') }} as p on p.contract_code = o.contract_code
    where o.underlying_close_price is not null
    group by o.mcx_commodity, o.trade_date
)

select
    f.mcx_commodity || ':' || cast(f.trade_date as varchar)                as commodity_day_id,
    f.mcx_commodity,
    f.commodity_id,
    f.segment,
    f.trade_date,
    f.is_latest,
    f.contract_code                                                         as flagship_contract_code,
    f.is_liquid,

    -- Price (flagship).
    f.close_price                                                           as flagship_close_price,
    f.return_1d,
    f.log_return_1d,
    -- Zero-mean realised variance, the convention volatility desks use: one
    -- session's squared log return. Summed and divided by sessions at query
    -- grain, × 252, it is the period's annualised variance.
    power(f.log_return_1d, 2)                                               as sq_log_return_1d,
    f.var_parkinson,
    f.var_garman_klass,
    f.var_rogers_satchell,
    case when f.return_1d > 0 then 1 else 0 end                             as is_up_session,
    f.rsi_14,
    f.garman_klass_vol_30d,
    f.roll_yield_annualised,
    case when f.is_contango then 1 else 0 end                               as is_contango_session,
    case when f.is_backwardation then 1 else 0 end                          as is_backwardation_session,
    f.trend_regime,
    f.volatility_regime,
    f.stance,
    p.premium_to_landed_pct,

    -- Activity and positioning (every code, every expiry).
    a.codes_trading,
    a.turnover_inr,
    a.mini_turnover_inr,
    {{ sf_safe_divide('a.turnover_inr', 'f.notional_per_lot_inr') }}       as volume_flagship_lots,
    a.open_interest_value_inr,
    o.put_oi_notional_inr,
    o.call_oi_notional_inr,
    o.option_premium_turnover_inr,
    o.option_notional_turnover_inr
from flagship as f
inner join activity as a on a.mcx_commodity = f.mcx_commodity and a.trade_date = f.trade_date
left join parity as p on p.mcx_commodity = f.mcx_commodity and p.trade_date = f.trade_date
left join options as o on o.mcx_commodity = f.mcx_commodity and o.trade_date = f.trade_date
