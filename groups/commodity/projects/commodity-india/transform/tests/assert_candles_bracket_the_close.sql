-- A session's high cannot be below its close, nor its low above it: the close
-- happened during the session, so it is inside the session's own range. A feed
-- that says otherwise is shipping a broken candle.
--
-- This is not hypothetical here. At the time of writing the Yahoo feed carried
-- 84 such days for coffee, 56 for cotton, 52 for cocoa, 37 for orange juice and
-- one for steel HRC — the softs and the continuation contracts, which points at
-- rollover stitching rather than a transient bad tick.
--
-- It matters because anything reading the candle as a range inherits the error.
-- `fct_commodity_trading_signals_daily` computes position in the 52-week range
-- and was printing 1.01 for steel HRC; it now widens the range to include the
-- close, which is definitionally correct and keeps the signal bounded. That fix
-- makes the metric right, not the data — so this test exists to keep the data
-- wrong out loud rather than quietly absorbed downstream.
--
-- Warn, not error: the rows are real observations and the close is the reliable
-- field in all of them, so failing the build would block a correct price board
-- over a defect nobody here can fix. Revisit if a feed change makes it rare
-- enough to demand.
{{ config(severity = 'warn') }}

select
    commodity_id,
    price_date,
    high_price,
    low_price,
    close_price
from {{ ref('fct_commodity_prices_daily') }}
where high_price is not null
    and low_price is not null
    and close_price is not null
    and (high_price < close_price or low_price > close_price)
