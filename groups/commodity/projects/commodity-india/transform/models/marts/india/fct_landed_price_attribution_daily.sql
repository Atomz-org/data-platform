-- Grain: one commodity per price date. Why the landed rupee price moved —
-- split into the benchmark, the rupee, and duty.
--
-- The question this exists for: an Indian buyer does not decide on the dollar
-- price, they decide on the landed rupee price, and the two diverge constantly.
-- Gold down 4% in USD against a rupee 4% weaker is a flat rupee price and no
-- opportunity at all, but a USD-only signal calls it a buy. Over 2021-2026 the
-- rupee moved one way for most of the span, so on a multi-year view the currency
-- is not a rounding error on the decision — it is frequently the decision.
--
-- The split also picks the response. A benchmark-led move is a commodity call:
-- buy, wait, hedge the underlying. An FX-led move is a treasury call: the same
-- tonnage costs more and no amount of commodity timing recovers it. A duty-led
-- move is neither — it is policy, it is a step rather than a drift, and it does
-- not mean-revert.
--
-- No conversion happens here. `fct_landed_prices_daily` has already done the
-- conformed sequence once — unit, FX, duty — and this model reads its outputs
-- and attributes the *change* in them. Re-deriving any leg would be that step
-- happening twice, which the family's price arithmetic forbids.
--
-- Method. The identity is multiplicative:
--     landed = benchmark_per_market_unit × fx × (1 + duty)
-- so log changes are additive and each factor's contribution is separable
-- without an interaction term to allocate arbitrarily. Contributions are then
-- rescaled onto the simple percentage change the page shows, so the three
-- always sum to the total a reader can check against the price column. A log
-- split with a residual would be more defensible in a paper and less checkable
-- on a screen; this is the trade made deliberately.
with landed as (
    select * from {{ ref('fct_landed_prices_daily') }}
),

lagged as (
    select
        price_id,
        market_code,
        commodity_id,
        price_date,
        market_unit,
        currency_code,
        benchmark_usd_per_market_unit,
        usd_fx_rate,
        effective_duty_rate,
        is_duty_rate_confirmed,
        is_import_prohibited,
        landed_price_local,
        -- 20 observations back: a month of trading, long enough that a single
        -- day's noise does not dominate the split and short enough that a buyer
        -- is still deciding about now.
        lag(landed_price_local, 20)            over w as landed_price_local_20d_ago,
        lag(benchmark_usd_per_market_unit, 20) over w as benchmark_20d_ago,
        lag(usd_fx_rate, 20)                   over w as fx_20d_ago,
        lag(effective_duty_rate, 20)           over w as duty_rate_20d_ago
    from landed
    window w as (partition by commodity_id order by price_date)
),

logs as (
    select
        *,
        -- Guarded: a zero or null on either side makes the ratio undefined, and
        -- ln(0) raises rather than returning null on some adapters. An
        -- unpriced or prohibited commodity legitimately has no benchmark, so
        -- this is an expected branch, not a defensive one.
        case when benchmark_20d_ago > 0 and benchmark_usd_per_market_unit > 0
             then ln(benchmark_usd_per_market_unit / benchmark_20d_ago) end as ln_benchmark,
        case when fx_20d_ago > 0 and usd_fx_rate > 0
             then ln(usd_fx_rate / fx_20d_ago) end                          as ln_fx,
        case when duty_rate_20d_ago is not null and effective_duty_rate is not null
             then ln((1 + effective_duty_rate) / (1 + duty_rate_20d_ago)) end as ln_duty
    from lagged
),

shares as (
    select
        *,
        ln_benchmark + ln_fx + ln_duty as ln_total,
        {{ sf_safe_divide('landed_price_local - landed_price_local_20d_ago',
                          'landed_price_local_20d_ago') }} as landed_change_20d_pct
    from logs
)

select
    price_id,
    market_code,
    commodity_id,
    price_date,
    market_unit,
    currency_code,
    is_duty_rate_confirmed,
    is_import_prohibited,

    landed_price_local,
    landed_price_local_20d_ago,
    landed_change_20d_pct,

    benchmark_usd_per_market_unit,
    benchmark_20d_ago,
    usd_fx_rate,
    fx_20d_ago,
    effective_duty_rate,
    duty_rate_20d_ago,

    -- Each contribution is that factor's share of the log move, applied to the
    -- simple move. The three sum to `landed_change_20d_pct` by construction, so
    -- a reader can add the columns and land on the price column — which is the
    -- property that makes this usable rather than merely correct.
    {{ sf_safe_divide('ln_benchmark', 'ln_total') }} * landed_change_20d_pct as benchmark_contribution_pct,
    {{ sf_safe_divide('ln_fx',        'ln_total') }} * landed_change_20d_pct as fx_contribution_pct,
    {{ sf_safe_divide('ln_duty',      'ln_total') }} * landed_change_20d_pct as duty_contribution_pct,

    -- Unsigned share of the rupee in the move, for ranking. abs() on both sides
    -- because the interesting case is a benchmark and a currency pulling in
    -- opposite directions — there the signed shares can exceed 1 and -1 while
    -- the honest statement is "these two nearly cancelled".
    {{ sf_safe_divide('abs(ln_fx)', 'abs(ln_benchmark) + abs(ln_fx) + abs(ln_duty)') }} as fx_share_of_move,

    case
        when ln_total is null then null
        when abs(ln_duty) > abs(ln_benchmark) and abs(ln_duty) > abs(ln_fx) then 'duty'
        when abs(ln_fx) > abs(ln_benchmark) then 'currency'
        else 'benchmark'
    end as primary_driver,

    row_number() over (partition by commodity_id order by price_date desc) = 1 as is_latest
from shares
