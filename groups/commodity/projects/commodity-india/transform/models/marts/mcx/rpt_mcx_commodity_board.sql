-- Grain: one MCX contract code. The latest session of every code, with the
-- nearest option chain beside it — the table behind the MCX summary page and
-- the headline of each commodity's page.
--
-- Staleness is against MCX's own latest session, not today's date: a code is
-- stale when the exchange settled others after its last row (a delisting, or a
-- job that is paused), and a Saturday is not stale for anyone.
with daily as (
    select * from {{ ref('fct_mcx_commodity_daily') }}
    where is_latest
),

chains as (
    select *
    from {{ ref('fct_mcx_options_daily') }}
    where is_latest and expiry_rank = 1
),

exchange_latest as (
    select max(trade_date) as latest_session from {{ ref('fct_mcx_commodity_daily') }}
)

select
    d.contract_code,
    d.mcx_commodity,
    d.commodity_id,
    d.contract_name,
    d.segment,
    d.is_flagship,
    d.is_liquid,
    d.trade_date                                                        as latest_trade_date,
    {{ sf_datediff('day', 'd.trade_date', 'e.latest_session') }}       as sessions_behind_days,
    d.trade_date < e.latest_session                                     as is_stale,
    d.active_contract_id,
    d.active_expiry_date,
    d.days_to_expiry,
    d.quote_size,
    d.quote_unit,
    d.lot_size,
    d.lot_unit,
    d.close_price,
    d.price_change,
    d.return_1d,
    d.return_5d,
    d.return_21d,
    d.return_63d,
    d.return_252d,
    d.return_ytd,
    d.notional_per_lot_inr,
    d.high_52w,
    d.low_52w,
    d.range_position_52w,
    d.drawdown_from_52w_peak,
    d.sma_50,
    d.sma_200,
    d.rsi_14,
    d.rsi_state,
    d.macd_histogram_pct,
    d.macd_crossover,
    d.atr_14,
    d.atr_14_pct,
    d.bollinger_pct_b,
    d.trend_regime,
    d.ma_crossover,
    d.cumulative_return,
    d.ema_9,
    d.ema_21,
    d.ema_200,
    d.ema_9_21_signal,
    d.ema_200_trend,
    d.realised_vol_20d,
    d.parkinson_vol_20d,
    d.close_vol_30d,
    d.parkinson_vol_30d,
    d.garman_klass_vol_30d,
    d.rogers_satchell_vol_30d,
    d.volatility_regime,
    d.volume_lots,
    d.relative_volume_20d,
    d.turnover_inr,
    d.open_interest_lots,
    d.open_interest_change_pct,
    d.open_interest_value_inr,
    d.oi_buildup,
    d.calendar_spread,
    d.annualised_carry,
    d.roll_yield_annualised,
    d.is_contango,
    d.is_backwardation,
    d.curve_state,
    d.rollover_pct,
    d.landed_parity_price,
    d.premium_to_landed_pct,
    d.stance,
    c.expiry_date                                                       as option_expiry_date,
    c.put_call_ratio_oi,
    c.put_call_ratio_volume,
    c.positioning                                                       as option_positioning,
    c.max_pain_strike,
    c.max_pain_distance_pct,
    c.call_wall_strike,
    c.put_wall_strike
from daily as d
cross join exchange_latest as e
left join chains as c on c.contract_code = d.contract_code
