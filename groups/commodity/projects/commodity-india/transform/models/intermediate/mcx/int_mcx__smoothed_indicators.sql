{{ config(materialized='table') }}
-- Grain: one MCX contract code per trading day. The indicators that are
-- recursive by definition: EMA(9), EMA(12), EMA(21), EMA(26), EMA(200), the
-- MACD signal line EMA(9) of MACD, and
-- Wilder's smoothing (α = 1/14) of gains, losses and true range for RSI(14)
-- and ATR(14).
--
-- A recursive CTE, not a window. An EMA truncated to a window is a different
-- number from the one every charting package prints, and a desk comparing our
-- RSI to its terminal's finds the gap on the first day. `with recursive` runs
-- on DuckDB and Snowflake alike, which a list-lambda trick would not. One
-- iteration per session and code — a few thousand steps of ~30 rows.
--
-- Seeded from the first observation, so the first ~3× period sessions carry
-- warm-up bias; the mart nulls them (`session_number` gates) rather than
-- print a confident number that is still converging.
--
-- On the back-adjusted series: a roll must not register as a gain or a range.
with recursive continuous as (
    select * from {{ ref('int_mcx__continuous_daily') }}
),

base as (
    select
        contract_code,
        session_number,
        trade_date,
        adj_close_price                                                     as px,
        coalesce(greatest(coalesce(adj_high_price, adj_close_price), prev_px)
                 - least(coalesce(adj_low_price, adj_close_price), prev_px),
                 coalesce(adj_high_price - adj_low_price, 0))               as true_range,
        coalesce(greatest(adj_close_price - prev_px, 0), 0)                 as gain,
        coalesce(greatest(prev_px - adj_close_price, 0), 0)                 as loss
    from (
        select
            *,
            lag(adj_close_price) over (partition by contract_code order by session_number) as prev_px
        from continuous
    ) as c
),

smoothed as (
    select
        contract_code,
        session_number,
        trade_date,
        px                                                                  as ema_9,
        px                                                                  as ema_12,
        px                                                                  as ema_21,
        px                                                                  as ema_26,
        px                                                                  as ema_200,
        cast(0 as double)                                                   as macd_signal,
        gain                                                                as avg_gain_14,
        loss                                                                as avg_loss_14,
        true_range                                                          as atr_14
    from base
    where session_number = 1

    union all

    select
        b.contract_code,
        b.session_number,
        b.trade_date,
        s.ema_9 + (2.0 / 10) * (b.px - s.ema_9),
        s.ema_12 + (2.0 / 13) * (b.px - s.ema_12),
        s.ema_21 + (2.0 / 22) * (b.px - s.ema_21),
        s.ema_26 + (2.0 / 27) * (b.px - s.ema_26),
        s.ema_200 + (2.0 / 201) * (b.px - s.ema_200),
        s.macd_signal + 0.2 * (
            (s.ema_12 + (2.0 / 13) * (b.px - s.ema_12))
            - (s.ema_26 + (2.0 / 27) * (b.px - s.ema_26))
            - s.macd_signal),
        s.avg_gain_14 + (b.gain - s.avg_gain_14) / 14.0,
        s.avg_loss_14 + (b.loss - s.avg_loss_14) / 14.0,
        s.atr_14 + (b.true_range - s.atr_14) / 14.0
    from smoothed as s
    inner join base as b
        on b.contract_code = s.contract_code
       and b.session_number = s.session_number + 1
)

select
    contract_code || ':' || cast(trade_date as varchar)                     as continuous_id,
    contract_code,
    trade_date,
    session_number,
    ema_9,
    ema_12,
    ema_21,
    ema_26,
    ema_200,
    ema_12 - ema_26                                                         as macd_line,
    macd_signal,
    (ema_12 - ema_26) - macd_signal                                         as macd_histogram,
    case
        when avg_loss_14 = 0 and avg_gain_14 = 0 then 50
        when avg_loss_14 = 0 then 100
        else 100 - 100 / (1 + avg_gain_14 / avg_loss_14)
    end                                                                     as rsi_14,
    atr_14
from smoothed
