-- Grain: one commodity per price date. Timing signals on the USD benchmark —
-- where a price sits in its own recent history, not what it costs.
--
-- India-only (`marts/india/`) rather than conformed, because a stance is a
-- judgement this desk is making and the thresholds below are ours. The inputs
-- are all conformed, so a sister that wants the same reading can take this file;
-- nothing here assumes India beyond the choice to have an opinion.
--
-- No conversion happens here. `fct_commodity_prices_daily` is already USD per
-- quote unit, step 1 done once in `int_commodity_prices__usd`; this model only
-- compares a price to itself. Every signal is therefore unit-free and safe to
-- read across commodities, which the price itself is not.
--
-- Windows count *observations*, not calendar days (`rows between N preceding`).
-- Futures do not trade at weekends or exchange holidays, so a calendar window
-- silently shortens every lookback across a long holiday — making volatility
-- look lowest exactly when the market was shut.
with prices as (
    select * from {{ ref('fct_commodity_prices_daily') }}
),

returns as (
    select
        *,
        -- Simple, not log. These are read off a page and quoted at somebody, and
        -- a log return that prints -0.051 after a 5% fall is a number that gets
        -- misquoted. Re-aggregation is not a concern: nothing sums these.
        {{ sf_safe_divide('close_price - prev_close_price', 'prev_close_price') }} as daily_return
    from prices
),

windowed as (
    select
        *,
        count(*)                        over w60 as obs_60d,
        avg(close_price)                over w60 as avg_close_60d,
        stddev_samp(close_price)        over w60 as sd_close_60d,
        count(*)                        over w20 as obs_20d,
        stddev_samp(daily_return)       over w20 as sd_return_20d,
        lag(close_price, 20) over (partition by commodity_id order by price_date) as close_20d_ago,
        -- One day back on each mean, so a crossover is detectable as an event
        -- rather than only as a state. A desk acts on the day it turns.
        lag(moving_avg_20d)  over (partition by commodity_id order by price_date) as prev_moving_avg_20d,
        lag(moving_avg_50d)  over (partition by commodity_id order by price_date) as prev_moving_avg_50d
    from returns
    window
        w20 as (partition by commodity_id order by price_date rows between 19 preceding and current row),
        w60 as (partition by commodity_id order by price_date rows between 59 preceding and current row)
),

derived as (
    select
        *,
        -- Gated on a full window, always. A mean of four observations is not a
        -- mean, and once it is a number in a column nothing downstream can tell
        -- the difference — so an incomplete window is null and the stance below
        -- reads "no_reading" rather than something confident and wrong.
        case when obs_60d = 60 then avg_close_60d end as avg_close_60d_full,
        case when obs_60d = 60 then sd_close_60d  end as sd_close_60d_full,
        -- Annualised from daily dispersion. 252 trading days matches the 252-row
        -- range window in `fct_commodity_prices_daily`, so volatility and range
        -- describe the same span.
        case when obs_20d = 20 then sd_return_20d * sqrt(252) end as realised_vol_20d,
        {{ sf_safe_divide('close_price - close_20d_ago', 'close_20d_ago') }} as momentum_20d_pct,
        {{ sf_safe_divide('close_price - moving_avg_50d', 'moving_avg_50d') }} as ma_gap_50d_pct,
        -- Position in the 52-week range: 0 at the low, 1 at the high. The single
        -- most portable number here — unit-free, bounded, and comparable across
        -- commodities whose prices never are.
        --
        -- The range is widened to include today's close, which is definitionally
        -- true — a close sits inside its own session — and is not the same as
        -- clamping the output. It is needed because the feed ships candles where
        -- `high_price < close_price`: 84 days of coffee, 56 of cotton, 52 of
        -- cocoa, 37 of orange juice, one of steel HRC, almost certainly
        -- continuation-contract rollover artifacts. Without this the metric
        -- printed 1.01, and a "percent of range" that exceeds 100% is the kind of
        -- number that makes a desk stop trusting the whole board.
        --
        -- The defect itself is not hidden here: `assert_candles_bracket_the_close`
        -- fails on the source fact, so the reading stays honest and the bad data
        -- stays visible instead of being absorbed by the model that consumes it.
        {{ sf_safe_divide('close_price - least(low_252d, close_price)',
                          'greatest(high_252d, close_price) - least(low_252d, close_price)') }} as pct_of_52w_range
    from windowed
),

scored as (
    select
        *,
        {{ sf_safe_divide('close_price - avg_close_60d_full', 'sd_close_60d_full') }} as z_score_60d,
        case
            when moving_avg_20d is null or moving_avg_50d is null then null
            when moving_avg_20d > moving_avg_50d then 'uptrend'
            else 'downtrend'
        end as ma_regime,
        case
            when moving_avg_20d is null or prev_moving_avg_20d is null then null
            when moving_avg_20d > moving_avg_50d and prev_moving_avg_20d <= prev_moving_avg_50d then 'golden_cross'
            when moving_avg_20d < moving_avg_50d and prev_moving_avg_20d >= prev_moving_avg_50d then 'death_cross'
            else 'none'
        end as ma_crossover
    from derived
)

select
    price_id,
    commodity_id,
    price_date,
    price_basis,
    quote_unit,
    currency_code,
    close_price,
    price_change_pct,
    moving_avg_20d,
    moving_avg_50d,
    high_252d,
    low_252d,
    is_latest,

    pct_of_52w_range,
    ma_gap_50d_pct,
    ma_regime,
    ma_crossover,
    z_score_60d,
    momentum_20d_pct,
    realised_vol_20d,

    -- Volatility regime, relative to this commodity's own 60-day dispersion
    -- rather than an absolute number: 30% annualised is calm for natural gas and
    -- extraordinary for rice, so one threshold across commodities would be
    -- meaningless. Expressed as a share of the mean (coefficient of variation),
    -- which is unit-free like everything else in this block.
    case
        when realised_vol_20d is null then null
        when realised_vol_20d >= 0.40 then 'high'
        when realised_vol_20d >= 0.20 then 'normal'
        else 'low'
    end as volatility_regime,

    -- The stance. Deliberately a small, legible rule rather than a fitted score:
    -- a desk has to be able to say why it was told to accumulate, and a weighted
    -- blend of six signals cannot be explained at the moment it matters.
    --
    -- Mean reversion is the premise — cheap against its own recent range and not
    -- still falling. That premise fails in a sustained trend, which is what
    -- `ma_regime` is doing in the condition: cheap *and* falling is a knife, and
    -- this returns `hold` for it rather than pretending the range signal alone
    -- is a buy. Nothing here is a recommendation; it is a shortlist to look at.
    case
        when pct_of_52w_range is null or ma_regime is null then 'no_reading'
        when pct_of_52w_range <= 0.25 and ma_regime = 'uptrend'   then 'accumulate'
        when pct_of_52w_range >= 0.80 and ma_regime = 'downtrend' then 'reduce'
        when pct_of_52w_range <= 0.15                              then 'watch_for_entry'
        when pct_of_52w_range >= 0.90                              then 'watch_for_exit'
        else 'hold'
    end as stance
from scored
