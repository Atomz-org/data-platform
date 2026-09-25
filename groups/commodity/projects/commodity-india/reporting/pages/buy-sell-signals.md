---
title: Buy / Sell Signals
queries:
  - metrics/avg_range_position.sql
  - metrics/avg_realised_vol.sql
  - metrics/avg_momentum_20d.sql
  - metrics/avg_fx_share_of_move.sql
---

A shortlist, not a recommendation. Everything here is a price compared to its own
recent history — nothing on this page knows what a commodity is worth, only where
it is sitting relative to where it has been.

Read it with the second half of the page. A benchmark that looks cheap in dollars
is not cheap to buy if the rupee moved further than the metal did, and the
**What Actually Moved** section below is the part that tells the two apart.

## Where the book stands today

```sql today
select
    stance,
    count(*) as commodities
from commodity_india.fct_commodity_trading_signals_daily
where is_latest
group by stance
```

```sql headline
select
    count(*) filter (where stance = 'accumulate')      as accumulate,
    count(*) filter (where stance = 'reduce')          as reduce,
    count(*) filter (where stance in ('watch_for_entry','watch_for_exit')) as watching,
    count(*) filter (where stance = 'no_reading')      as no_reading,
    max(price_date)                                    as as_of
from commodity_india.fct_commodity_trading_signals_daily
where is_latest
```

<Grid cols=5>

<BigValue data={headline} value=accumulate title='Accumulate' fmt=num0/>
<BigValue data={headline} value=reduce title='Reduce' fmt=num0/>
<BigValue data={headline} value=watching title='Watching' fmt=num0/>
<BigValue data={headline} value=no_reading title='No reading yet' fmt=num0/>
<BigValue data={headline} value=as_of title='As of'/>

</Grid>

**No reading** is not a gap in the data — it is a commodity whose 50-day mean or
52-week range is not yet full, or one priced from a carried-forward indicative
level rather than a daily feed. A stance would be a guess, so there is not one.

## The shortlist

Sorted by position in the 52-week range: cheapest against its own year at the top.

```sql shortlist
select
    s.commodity_id,
    c.commodity_name,
    c.category,
    s.close_price,
    s.pct_of_52w_range,
    s.ma_regime,
    s.momentum_20d_pct,
    s.realised_vol_20d,
    s.volatility_regime,
    s.stance
from commodity_india.fct_commodity_trading_signals_daily s
inner join commodity_india.dim_commodities c on c.commodity_id = s.commodity_id
where s.is_latest
  and s.stance <> 'no_reading'
order by s.pct_of_52w_range
```

<DataTable data={shortlist} rows=25 search=true>
    <Column id=commodity_name title='Commodity'/>
    <Column id=category title='Category'/>
    <Column id=close_price title='Close (USD)' fmt=num2/>
    <Column id=pct_of_52w_range title='52w Range' fmt=pct0 contentType=colorscale colorScale={['#d4691a','#eeeeee','#2e7d32']} scaleColumnMax=1/>
    <Column id=ma_regime title='Trend'/>
    <Column id=momentum_20d_pct title='20d Move' fmt=pct1 contentType=delta/>
    <Column id=realised_vol_20d title='Vol (ann.)' fmt=pct0/>
    <Column id=stance title='Stance'/>
</DataTable>

The colour on **52w Range** runs low-to-high, so the orange end is the bottom of
the year. That is where a mean-reversion buyer looks first — and precisely where
a commodity in a genuine downtrend also sits, which is why the stance column
disagrees with the colour sometimes. `accumulate` requires cheap **and** an
uptrend; cheap and still falling returns `hold`.

## Crossovers — the day the trend turned

A regime change is worth more than a regime: the state has been true for weeks,
the turn happened today.

```sql crossovers
select
    s.price_date,
    c.commodity_name,
    s.ma_crossover,
    s.close_price,
    s.pct_of_52w_range
from commodity_india.fct_commodity_trading_signals_daily s
inner join commodity_india.dim_commodities c on c.commodity_id = s.commodity_id
where s.ma_crossover in ('golden_cross', 'death_cross')
  and s.price_date >= (select max(price_date) - interval 90 day
                       from commodity_india.fct_commodity_trading_signals_daily)
order by s.price_date desc
```

<DataTable data={crossovers} rows=12>
    <Column id=price_date title='Date'/>
    <Column id=commodity_name title='Commodity'/>
    <Column id=ma_crossover title='Crossover'/>
    <Column id=close_price title='Close (USD)' fmt=num2/>
    <Column id=pct_of_52w_range title='52w Range' fmt=pct0/>
</DataTable>

## What actually moved — benchmark, rupee, or duty

This is the part a dollar-denominated screen cannot tell you. The landed rupee
price is `benchmark × USD/INR × (1 + duty)`, so a move in any of the three lands
on the same invoice. The three contributions sum to the total — they are meant to
be added up and checked against the price.

```sql attribution
select
    a.commodity_id,
    c.commodity_name,
    a.landed_change_20d_pct,
    a.benchmark_contribution_pct,
    a.fx_contribution_pct,
    a.duty_contribution_pct,
    a.fx_share_of_move,
    a.primary_driver
from commodity_india.fct_landed_price_attribution_daily a
inner join commodity_india.dim_commodities c on c.commodity_id = a.commodity_id
where a.is_latest
  and a.landed_change_20d_pct is not null
  and not a.is_import_prohibited
order by abs(a.landed_change_20d_pct) desc
```

<DataTable data={attribution} rows=25 search=true>
    <Column id=commodity_name title='Commodity'/>
    <Column id=landed_change_20d_pct title='Landed ₹ 20d' fmt=pct1 contentType=delta/>
    <Column id=benchmark_contribution_pct title='of which: Benchmark' fmt=pct1/>
    <Column id=fx_contribution_pct title='of which: Rupee' fmt=pct1/>
    <Column id=duty_contribution_pct title='of which: Duty' fmt=pct1/>
    <Column id=primary_driver title='Driver'/>
</DataTable>

**How to act on the driver column.** `benchmark` is a commodity call — time it,
or hedge the underlying. `currency` is a treasury call, and no amount of
commodity timing recovers it; the lever is forward cover, not entry price.
`duty` is policy: a step rather than a drift, and unlike the other two it does
not mean-revert, so waiting it out is not a strategy.

```sql driver_mix
select
    primary_driver,
    count(*) as commodities
from commodity_india.fct_landed_price_attribution_daily
where is_latest and primary_driver is not null
group by primary_driver
```

<BarChart
    data={driver_mix}
    x=primary_driver
    y=commodities
    title='What is driving the landed price right now'
    swapXY=true
/>

## Caveats worth keeping in view

- **The feed ships broken candles.** 528 sessions carry a high below their close
  or a low above it — 177 coffee, 141 cotton, 132 cocoa, 77 orange juice, 1 steel
  HRC — almost certainly continuation-contract rollover artifacts. The range
  metric is bounded against it by construction, and
  `assert_candles_bracket_the_close` keeps the defect visible rather than letting
  it be absorbed silently.
- **Nine commodities have no free feed.** Their level is an indicative one that
  moves only when a newer `as_of_date` is appended, so a range position computed
  from it is describing the seed, not the market.
- **Duty before June 2026 is unconfirmed** and back-applied (ADR-0001), so a
  duty contribution on an older row is a reconstruction.
- **Futures do not settle at weekends.** Every window here counts observations,
  not calendar days, so a long holiday shortens nothing.
