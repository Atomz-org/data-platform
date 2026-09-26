-- Grain: one MCX contract code per trading day, on the continuous most-active
-- series (`int_mcx__continuous_daily`). The fact every commodity page reads.
--
-- Three families of numbers, all computed here and nowhere in a page:
--   * price and trend — returns over 1/5/21/63/252 sessions and year to date,
--     SMA 20/50/200, EMA/MACD, RSI(14), ATR(14), Bollinger(20, 2), the 52-week
--     range and drawdown;
--   * risk — close-to-close volatility and the range estimators (Parkinson,
--     Garman–Klass, Rogers–Satchell) over 14/30/90 sessions, annualised on
--     252, and a regime against the code's own year;
--   * the curve and positioning — open-interest build-up across all expiries,
--     near/next calendar spread and its annualised carry, rollover share, and
--     MCX's premium to the landed import parity where the family prices the
--     underlying.
--
-- Windows count sessions (`rows between`), not calendar days: MCX closes on
-- weekends and exchange holidays, and a calendar window quietly shrinks across
-- Diwali. Every windowed number is null until its window is full; a 200-day
-- average of forty days is not one. Indicators use back-adjusted prices, so a
-- roll is never a signal; `close_price` is the real settlement.
with c as (
    select * from {{ ref('int_mcx__continuous_daily') }}
),

smooth as (
    select * from {{ ref('int_mcx__smoothed_indicators') }}
),

parity as (
    select contract_code, price_date, quote_equivalent_inr
    from {{ ref('fct_mcx_lot_equivalents_daily') }}
),

ranges as (
    -- One session's range variance under each estimator, in log terms of the
    -- active contract's own OHLC (unadjusted — a ratio inside one session is
    -- the same on either scale). u = ln(H/O), d = ln(L/O), k = ln(C/O).
    --   Parkinson (1980):        (u − d)² / (4 ln 2)
    --   Garman–Klass (1980), the "best analytic" σ̂²:
    --                            0.511(u − d)² − 0.019[k(u + d) − 2ud] − 0.383k²
    --   Rogers–Satchell (1991):  u(u − k) + d(d − k)   — drift-robust
    -- Null on a session without a full traded OHLC (MCX prints zeros then).
    select
        c.*,
        case when open_price > 0 and high_price > 0 and low_price > 0
             then ln(high_price / open_price) end                       as u,
        case when open_price > 0 and high_price > 0 and low_price > 0
             then ln(low_price / open_price) end                        as d,
        case when open_price > 0 and close_price > 0 and high_price > 0 and low_price > 0
             then ln(close_price / open_price) end                      as k
    from c
),

variances as (
    select
        *,
        power(u - d, 2) / (4 * ln(2))                                   as var_parkinson,
        0.511 * power(u - d, 2) - 0.019 * (k * (u + d) - 2 * u * d) - 0.383 * power(k, 2)
                                                                        as var_garman_klass,
        u * (u - k) + d * (d - k)                                       as var_rogers_satchell
    from ranges
),

windowed as (
    select
        c.*,
        {%- for n in [14, 30, 90] %}
        count(c.var_garman_klass)       over (partition by contract_code order by trade_date
                                              rows between {{ n - 1 }} preceding and current row) as obs_range_{{ n }},
        avg(c.var_parkinson)            over (partition by contract_code order by trade_date
                                              rows between {{ n - 1 }} preceding and current row) as mean_var_parkinson_{{ n }},
        avg(c.var_garman_klass)         over (partition by contract_code order by trade_date
                                              rows between {{ n - 1 }} preceding and current row) as mean_var_garman_klass_{{ n }},
        avg(c.var_rogers_satchell)      over (partition by contract_code order by trade_date
                                              rows between {{ n - 1 }} preceding and current row) as mean_var_rogers_satchell_{{ n }},
        count(*)                        over (partition by contract_code order by trade_date
                                              rows between {{ n - 1 }} preceding and current row) as obs_{{ n }},
        stddev_samp(c.log_return)       over (partition by contract_code order by trade_date
                                              rows between {{ n - 1 }} preceding and current row) as sd_log_return_{{ n }},
        {%- endfor %}
        sum(c.log_return) over (partition by contract_code order by trade_date
                                rows between unbounded preceding and current row) as cum_log_return,
        count(*)                        over w20  as obs_20,
        count(case when is_traded then 1 end) over w20 as traded_sessions_20,
        count(*)                        over w50  as obs_50,
        count(*)                        over w200 as obs_200,
        count(*)                        over w252 as obs_252,
        avg(adj_close_price)            over w20  as sma_20,
        avg(adj_close_price)            over w50  as sma_50,
        avg(adj_close_price)            over w200 as sma_200,
        stddev_samp(adj_close_price)    over w20  as sd_close_20,
        stddev_samp(log_return)         over w20  as sd_log_return_20,
        -- Parkinson: the day's high-low range carries more information than
        -- its close-to-close move. Untraded days have no range and drop out.
        avg(case when adj_high_price > 0 and adj_low_price > 0
                 then power(ln(adj_high_price / adj_low_price), 2) end) over w20 as mean_sq_hl_20,
        count(case when adj_high_price > 0 and adj_low_price > 0 then 1 end) over w20 as obs_hl_20,
        max(coalesce(adj_high_price, adj_close_price)) over w252 as high_252,
        min(coalesce(adj_low_price, adj_close_price))  over w252 as low_252,
        max(adj_close_price)            over w252 as peak_close_252,
        avg(volume_lots_all) over (
            partition by contract_code order by trade_date
            rows between 20 preceding and 1 preceding)  as avg_volume_lots_prev_20,
        lag(adj_close_price, 5)   over o as adj_close_5,
        lag(adj_close_price, 21)  over o as adj_close_21,
        lag(adj_close_price, 63)  over o as adj_close_63,
        lag(adj_close_price, 252) over o as adj_close_252,
        lag(adj_close_price)      over o as adj_close_prev
    from variances as c
    window
        o    as (partition by contract_code order by trade_date),
        w20  as (partition by contract_code order by trade_date rows between 19 preceding and current row),
        w50  as (partition by contract_code order by trade_date rows between 49 preceding and current row),
        w200 as (partition by contract_code order by trade_date rows between 199 preceding and current row),
        w252 as (partition by contract_code order by trade_date rows between 251 preceding and current row)
),

derived as (
    select
        w.*,
        s.ema_12,
        s.ema_26,
        s.macd_line,
        s.macd_signal,
        s.macd_histogram,
        s.rsi_14,
        s.atr_14,
        first_value(w.adj_close_prev) over (
            partition by w.contract_code, extract(year from w.trade_date)
            order by w.trade_date)                                        as adj_close_prev_year_end,
        case when w.obs_20 = 20 then w.sma_20 end                         as sma_20_full,
        case when w.obs_50 = 50 then w.sma_50 end                         as sma_50_full,
        case when w.obs_200 = 200 then w.sma_200 end                      as sma_200_full,
        case when w.obs_20 = 20 then w.sd_log_return_20 * sqrt(252) end   as realised_vol_20d,
        case when w.obs_hl_20 >= 15 then sqrt(w.mean_sq_hl_20 / (4 * ln(2))) * sqrt(252) end
                                                                          as parkinson_vol_20d,
        s.ema_9,
        s.ema_21,
        s.ema_200,
        {%- for n in [14, 30, 90] %}
        -- A window is published once 80% of its sessions carry a full range.
        case when w.obs_{{ n }} = {{ n }} then w.sd_log_return_{{ n }} * sqrt(252) end as close_vol_{{ n }}d,
        case when w.obs_range_{{ n }} >= {{ (n * 0.8) | round(0, 'ceil') | int }}
             then sqrt(greatest(w.mean_var_parkinson_{{ n }}, 0) * 252) end        as parkinson_vol_{{ n }}d,
        case when w.obs_range_{{ n }} >= {{ (n * 0.8) | round(0, 'ceil') | int }}
             then sqrt(greatest(w.mean_var_garman_klass_{{ n }}, 0) * 252) end      as garman_klass_vol_{{ n }}d,
        case when w.obs_range_{{ n }} >= {{ (n * 0.8) | round(0, 'ceil') | int }}
             then sqrt(greatest(w.mean_var_rogers_satchell_{{ n }}, 0) * 252) end   as rogers_satchell_vol_{{ n }}d,
        {%- endfor %}
        exp(w.cum_log_return) - 1                                         as cumulative_return
    from windowed as w
    inner join smooth as s on s.continuous_id = w.continuous_id
),

scored as (
    select
        d.*,
        avg(realised_vol_20d) over (
            partition by contract_code order by trade_date
            rows between 251 preceding and current row)                   as avg_realised_vol_252,
        lag(sma_50_full)    over (partition by contract_code order by trade_date) as prev_sma_50,
        lag(sma_200_full)   over (partition by contract_code order by trade_date) as prev_sma_200,
        lag(macd_histogram) over (partition by contract_code order by trade_date) as prev_macd_histogram,
        lag(ema_9)          over (partition by contract_code order by trade_date) as prev_ema_9,
        lag(ema_21)         over (partition by contract_code order by trade_date) as prev_ema_21
    from derived as d
),

final as (
    select
        s.*,
        -- Warm-up gates for the recursive indicators: three periods of the
        -- slowest input before a number is published.
        case when session_number >= 78 then macd_line end                 as macd_line_ready,
        case when session_number >= 78 then macd_signal end               as macd_signal_ready,
        case when session_number >= 78 then macd_histogram end            as macd_histogram_ready,
        case when session_number >= 42 then rsi_14 end                    as rsi_14_ready,
        case when session_number >= 42 then atr_14 end                    as atr_14_ready,
        case when obs_20 = 20 then sma_20 + 2 * sd_close_20 end           as bollinger_upper,
        case when obs_20 = 20 then sma_20 - 2 * sd_close_20 end           as bollinger_lower,
        {{ mcx_oi_buildup('daily_return', 'open_interest_change_lots_all') }} as oi_buildup
    from scored as s
)

select
    f.continuous_id,
    f.contract_code,
    f.mcx_commodity,
    f.commodity_id,
    f.contract_name,
    f.segment,
    f.is_flagship,
    f.trade_date,
    f.session_number,
    max(f.trade_date) over (partition by f.contract_code) = f.trade_date  as is_latest,
    f.active_contract_id,
    f.active_expiry_date,
    f.days_to_expiry,
    f.is_roll_day,
    f.quote_size,
    f.quote_unit,
    f.lot_size,
    f.lot_unit,
    f.quote_units_per_lot,
    f.is_traded,
    -- Traded on at least half of its last 20 sessions. An untraded MCX contract
    -- carries its settlement forward, so its indicators describe the carry,
    -- not a market; the stance says `illiquid` instead of reading them.
    f.traded_sessions_20 >= 10                                            as is_liquid,

    -- Price: the real settlement of the active contract, and its session.
    f.open_price,
    f.high_price,
    f.low_price,
    f.close_price,
    f.previous_close_price,
    f.price_change,
    f.notional_per_lot_inr,
    f.adj_close_price,

    -- Returns (roll-free).
    f.daily_return                                                        as return_1d,
    f.log_return                                                          as log_return_1d,
    f.cumulative_return,
    {{ sf_safe_divide('f.adj_close_price', 'f.adj_close_5') }} - 1        as return_5d,
    {{ sf_safe_divide('f.adj_close_price', 'f.adj_close_21') }} - 1       as return_21d,
    {{ sf_safe_divide('f.adj_close_price', 'f.adj_close_63') }} - 1       as return_63d,
    {{ sf_safe_divide('f.adj_close_price', 'f.adj_close_252') }} - 1      as return_252d,
    {{ sf_safe_divide('f.adj_close_price', 'f.adj_close_prev_year_end') }} - 1 as return_ytd,

    -- Trend, restated in real-price terms (adjusted ÷ adj_factor) so a page can
    -- draw them on the same axis as the close.
    f.sma_20_full / f.adj_factor                                          as sma_20,
    f.sma_50_full / f.adj_factor                                          as sma_50,
    f.sma_200_full / f.adj_factor                                         as sma_200,
    case when f.session_number >= 27  then f.ema_9 / f.adj_factor end     as ema_9,
    case when f.session_number >= 36  then f.ema_12 / f.adj_factor end    as ema_12,
    case when f.session_number >= 63  then f.ema_21 / f.adj_factor end    as ema_21,
    case when f.session_number >= 78  then f.ema_26 / f.adj_factor end    as ema_26,
    case when f.session_number >= 600 then f.ema_200 / f.adj_factor end   as ema_200,
    -- EMA 9/21: the fast momentum crossover. Gated like the averages it reads.
    case
        when f.session_number < 63 or f.prev_ema_9 is null then null
        when f.ema_9 > f.ema_21 and f.prev_ema_9 <= f.prev_ema_21 then 'bullish_cross'
        when f.ema_9 < f.ema_21 and f.prev_ema_9 >= f.prev_ema_21 then 'bearish_cross'
        when f.ema_9 > f.ema_21 then 'above'
        else 'below'
    end                                                                   as ema_9_21_signal,
    case
        when f.session_number < 600 then null
        when f.adj_close_price > f.ema_200 then 'above'
        else 'below'
    end                                                                   as ema_200_trend,
    f.bollinger_upper / f.adj_factor                                      as bollinger_upper,
    f.bollinger_lower / f.adj_factor                                      as bollinger_lower,
    {{ sf_safe_divide('f.adj_close_price - f.bollinger_lower', 'f.bollinger_upper - f.bollinger_lower') }}
                                                                          as bollinger_pct_b,
    {{ sf_safe_divide('f.bollinger_upper - f.bollinger_lower', 'f.sma_20_full') }} as bollinger_bandwidth,
    -- MACD as a share of price, so it compares across codes and through time.
    {{ sf_safe_divide('f.macd_line_ready', 'f.adj_close_price') }}        as macd_line_pct,
    {{ sf_safe_divide('f.macd_signal_ready', 'f.adj_close_price') }}      as macd_signal_pct,
    {{ sf_safe_divide('f.macd_histogram_ready', 'f.adj_close_price') }}   as macd_histogram_pct,
    f.rsi_14_ready                                                        as rsi_14,
    f.atr_14_ready / f.adj_factor                                         as atr_14,
    {{ sf_safe_divide('f.atr_14_ready', 'f.adj_close_price') }}           as atr_14_pct,
    case when f.obs_252 = 252 then f.high_252 / f.adj_factor end          as high_52w,
    case when f.obs_252 = 252 then f.low_252 / f.adj_factor end           as low_52w,
    case when f.obs_252 = 252 then
        {{ sf_safe_divide('f.adj_close_price - least(f.low_252, f.adj_close_price)',
                          'greatest(f.high_252, f.adj_close_price) - least(f.low_252, f.adj_close_price)') }}
    end                                                                   as range_position_52w,
    {{ sf_safe_divide('f.adj_close_price', 'f.peak_close_252') }} - 1     as drawdown_from_52w_peak,
    case
        when f.sma_50_full is null or f.sma_200_full is null then null
        when f.adj_close_price > f.sma_200_full and f.sma_50_full > f.sma_200_full then 'uptrend'
        when f.adj_close_price < f.sma_200_full and f.sma_50_full < f.sma_200_full then 'downtrend'
        else 'range'
    end                                                                   as trend_regime,
    case
        when f.prev_sma_50 is null or f.prev_sma_200 is null then null
        when f.sma_50_full > f.sma_200_full and f.prev_sma_50 <= f.prev_sma_200 then 'golden_cross'
        when f.sma_50_full < f.sma_200_full and f.prev_sma_50 >= f.prev_sma_200 then 'death_cross'
        else 'none'
    end                                                                   as ma_crossover,
    case
        when f.macd_histogram_ready is null or f.prev_macd_histogram is null then null
        when f.macd_histogram_ready > 0 and f.prev_macd_histogram <= 0 then 'bullish_cross'
        when f.macd_histogram_ready < 0 and f.prev_macd_histogram >= 0 then 'bearish_cross'
        else 'none'
    end                                                                   as macd_crossover,
    case
        when f.rsi_14_ready is null then null
        when f.rsi_14_ready >= 70 then 'overbought'
        when f.rsi_14_ready <= 30 then 'oversold'
        else 'neutral'
    end                                                                   as rsi_state,

    -- Risk. Close-to-close vs the range estimators: when Garman–Klass runs
    -- well above close-to-close, the day's swings are wider than its net move.
    f.realised_vol_20d,
    f.parkinson_vol_20d,
    -- One session's variance under each range estimator (null on an untraded
    -- session). Published so a period volatility can be re-derived over any
    -- window as √(252 · mean σ²ᵢ) — averaging rolling volatilities cannot.
    f.var_parkinson,
    f.var_garman_klass,
    f.var_rogers_satchell,
    {%- for n in [14, 30, 90] %}
    f.close_vol_{{ n }}d,
    f.parkinson_vol_{{ n }}d,
    f.garman_klass_vol_{{ n }}d,
    f.rogers_satchell_vol_{{ n }}d,
    {%- endfor %}
    case
        when f.realised_vol_20d is null or f.avg_realised_vol_252 is null then null
        when f.realised_vol_20d >= 1.25 * f.avg_realised_vol_252 then 'high'
        when f.realised_vol_20d <= 0.80 * f.avg_realised_vol_252 then 'low'
        else 'normal'
    end                                                                   as volatility_regime,

    -- Activity and positioning, across every open expiry.
    f.open_expiries,
    f.volume_lots_all                                                     as volume_lots,
    {{ sf_safe_divide('f.volume_lots_all', 'f.avg_volume_lots_prev_20') }} as relative_volume_20d,
    f.turnover_inr_all                                                    as turnover_inr,
    f.open_interest_lots_all                                              as open_interest_lots,
    f.open_interest_change_lots_all                                       as open_interest_change_lots,
    {{ sf_safe_divide('f.open_interest_change_lots_all',
                      'f.open_interest_lots_all - f.open_interest_change_lots_all') }}
                                                                          as open_interest_change_pct,
    f.open_interest_value_inr_all                                         as open_interest_value_inr,
    f.oi_buildup,

    -- The curve.
    f.near_expiry_date,
    f.next_expiry_date,
    f.near_close_price,
    f.next_close_price,
    f.next_close_price - f.near_close_price                               as calendar_spread,
    -- Annualised cost of carry implied by the near/next spread.
    case when f.next_expiry_date > f.near_expiry_date then
        ({{ sf_safe_divide('f.next_close_price', 'f.near_close_price') }} - 1)
        * 365.0 / {{ sf_datediff('day', 'f.near_expiry_date', 'f.next_expiry_date') }}
    end                                                                   as annualised_carry,
    -- Roll yield to a long who rolls near into next, annualised: negative in
    -- contango (sell the cheap expiring month, buy the dearer one), positive
    -- in backwardation. The near month stands in for spot — MCX's bhavcopy
    -- has no spot price.
    case when f.next_expiry_date > f.near_expiry_date then
        ({{ sf_safe_divide('f.near_close_price', 'f.next_close_price') }} - 1)
        * 365.0 / {{ sf_datediff('day', 'f.near_expiry_date', 'f.next_expiry_date') }}
    end                                                                   as roll_yield_annualised,
    f.next_close_price > f.near_close_price                               as is_contango,
    f.next_close_price < f.near_close_price                               as is_backwardation,
    case
        when f.next_close_price is null or f.near_close_price is null then null
        when f.next_close_price > f.near_close_price then 'contango'
        when f.next_close_price < f.near_close_price then 'backwardation'
        else 'flat'
    end                                                                   as curve_state,
    -- Share of open interest already in later expiries: read near expiry, it
    -- is how much of the book has rolled.
    {{ sf_safe_divide('f.deferred_open_interest_lots', 'f.open_interest_lots_all') }} as rollover_pct,

    -- MCX against the landed import parity the rest of this project computes
    -- (benchmark × USD/INR × (1 + duty), per the same quote basis). Positive:
    -- MCX is dearer than importing. Only codes in `mcx_contract_lots`.
    p.quote_equivalent_inr                                                as landed_parity_price,
    {{ sf_safe_divide('f.close_price', 'p.quote_equivalent_inr') }} - 1   as premium_to_landed_pct,

    -- The stance: a small, legible rule, in the house style of
    -- `fct_commodity_trading_signals_daily`. Trend (50/200) decides the side,
    -- momentum (RSI, MACD) and positioning (OI build-up) decide the timing.
    -- A shortlist to look at, not an order.
    case
        when f.traded_sessions_20 < 10 then 'illiquid'
        when f.sma_200_full is null or f.rsi_14_ready is null or f.macd_histogram_ready is null then 'no_reading'
        when f.rsi_14_ready >= 75 then 'overextended_up'
        when f.rsi_14_ready <= 25 then 'overextended_down'
        when f.adj_close_price > f.sma_200_full and f.sma_50_full > f.sma_200_full and f.rsi_14_ready < 40
            then 'buy_the_dip'
        when f.adj_close_price < f.sma_200_full and f.sma_50_full < f.sma_200_full and f.rsi_14_ready > 60
            then 'sell_the_rally'
        when f.adj_close_price > f.sma_200_full and f.macd_histogram_ready > 0 and f.oi_buildup = 'long_buildup'
            then 'trend_long'
        when f.adj_close_price < f.sma_200_full and f.macd_histogram_ready < 0 and f.oi_buildup = 'short_buildup'
            then 'trend_short'
        else 'neutral'
    end                                                                   as stance
from final as f
left join parity as p
    on p.contract_code = f.contract_code and p.price_date = f.trade_date
