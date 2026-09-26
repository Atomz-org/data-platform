-- source extract for fct_commodity_trading_signals_daily (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    price_id,
    commodity_id,
    price_date,
    close_price,
    pct_of_52w_range,
    ma_gap_50d_pct,
    ma_regime,
    ma_crossover,
    z_score_60d,
    momentum_20d_pct,
    realised_vol_20d,
    volatility_regime,
    stance,
    is_latest,
    price_basis,
    quote_unit,
    currency_code,
    price_change_pct,
    moving_avg_20d,
    moving_avg_50d,
    high_252d,
    low_252d
from main_marts.fct_commodity_trading_signals_daily
