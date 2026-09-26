-- Grain: one MCX contract code per trading day. The continuous series a chart
-- and every indicator reads, plus what the whole curve did that day.
--
-- Which contract represents the day: the most active, by open interest — where
-- the market has actually rolled to — with the nearer expiry winning a tie.
-- Rolling on a calendar rule instead (N days before expiry) picks a month the
-- desk has already left, and its thin last days print as volatility.
--
-- Returns are taken inside one contract (close ÷ that contract's own previous
-- settlement), never across the roll. A continuous close stitched from two
-- expiries jumps by the calendar spread on the roll day, and a 3% contango step
-- read as a 3% move is the classic continuous-futures bug. `adj_*` prices are
-- back-adjusted by ratio from those returns: the latest day equals the real
-- close, earlier days are scaled so the series has no roll gaps. Indicators use
-- `adj_*`; anything quoted as a price to trade at uses the real close.
with sessions as (
    select * from {{ ref('int_mcx__futures_sessions') }}
),

picked as (
    select
        *,
        row_number() over (
            partition by contract_code, trade_date
            order by open_interest_lots desc, expiry_date
        ) as activity_rank
    from sessions
),

curve as (
    -- What every open expiry did together that day.
    select
        contract_code,
        trade_date,
        count(*)                                                        as open_expiries,
        sum(volume_lots)                                                as volume_lots_all,
        sum(open_interest_lots)                                         as open_interest_lots_all,
        sum(open_interest_change_lots)                                  as open_interest_change_lots_all,
        sum(turnover_inr)                                               as turnover_inr_all,
        sum(open_interest_value_inr)                                    as open_interest_value_inr_all,
        max(case when expiry_rank = 1 then close_price end)             as near_close_price,
        max(case when expiry_rank = 2 then close_price end)             as next_close_price,
        max(case when expiry_rank = 1 then expiry_date end)             as near_expiry_date,
        max(case when expiry_rank = 2 then expiry_date end)             as next_expiry_date,
        sum(case when expiry_rank = 1 then open_interest_lots else 0 end) as near_open_interest_lots,
        sum(case when expiry_rank > 1 then open_interest_lots else 0 end) as deferred_open_interest_lots
    from sessions
    group by contract_code, trade_date
),

active as (
    select
        p.*,
        c.open_expiries,
        c.volume_lots_all,
        c.open_interest_lots_all,
        c.open_interest_change_lots_all,
        c.turnover_inr_all,
        c.open_interest_value_inr_all,
        c.near_close_price,
        c.next_close_price,
        c.near_expiry_date,
        c.next_expiry_date,
        c.near_open_interest_lots,
        c.deferred_open_interest_lots,
        -- The return the day earned, inside the active contract. A first
        -- observation of a contract has no previous settlement and earns none.
        coalesce({{ sf_safe_divide('p.close_price - p.previous_close_price', 'p.previous_close_price') }}, 0)
                                                                        as daily_return
    from picked as p
    inner join curve as c
        on c.contract_code = p.contract_code and c.trade_date = p.trade_date
    where p.activity_rank = 1
),

indexed as (
    select
        *,
        row_number() over (partition by contract_code order by trade_date)  as session_number,
        sum(ln(1 + daily_return)) over (
            partition by contract_code order by trade_date
            rows between unbounded preceding and current row)               as cum_log_return,
        sum(ln(1 + daily_return)) over (partition by contract_code)         as total_log_return,
        last_value(close_price) over (
            partition by contract_code order by trade_date
            rows between unbounded preceding and unbounded following)       as latest_close_price,
        lag(contract_id) over (partition by contract_code order by trade_date) as prev_contract_id
    from active
)

select
    contract_code || ':' || cast(trade_date as varchar)                     as continuous_id,
    contract_code,
    mcx_commodity,
    commodity_id,
    contract_name,
    segment,
    is_flagship,
    trade_date,
    session_number,
    contract_id                                                             as active_contract_id,
    expiry_date                                                             as active_expiry_date,
    days_to_expiry,
    expiry_bucket                                                           as active_expiry_bucket,
    prev_contract_id is not null and prev_contract_id <> contract_id       as is_roll_day,
    quote_size,
    quote_unit,
    lot_size,
    lot_unit,
    quote_units_per_lot,
    is_traded,
    open_price,
    high_price,
    low_price,
    close_price,
    previous_close_price,
    price_change,
    daily_return,
    ln(1 + daily_return)                                                    as log_return,
    -- Back-adjustment factor: 1 on the latest day, the product of every later
    -- day's return inverted before it.
    exp(cum_log_return - total_log_return) * latest_close_price / nullif(close_price, 0)
                                                                            as adj_factor,
    exp(cum_log_return - total_log_return) * latest_close_price            as adj_close_price,
    open_price * exp(cum_log_return - total_log_return) * latest_close_price / nullif(close_price, 0)
                                                                            as adj_open_price,
    high_price * exp(cum_log_return - total_log_return) * latest_close_price / nullif(close_price, 0)
                                                                            as adj_high_price,
    low_price * exp(cum_log_return - total_log_return) * latest_close_price / nullif(close_price, 0)
                                                                            as adj_low_price,
    volume_lots                                                             as active_volume_lots,
    open_interest_lots                                                      as active_open_interest_lots,
    open_interest_change_lots                                               as active_open_interest_change_lots,
    notional_per_lot_inr,
    open_expiries,
    volume_lots_all,
    open_interest_lots_all,
    open_interest_change_lots_all,
    turnover_inr_all,
    open_interest_value_inr_all,
    near_close_price,
    next_close_price,
    near_expiry_date,
    next_expiry_date,
    near_open_interest_lots,
    deferred_open_interest_lots
from indexed
