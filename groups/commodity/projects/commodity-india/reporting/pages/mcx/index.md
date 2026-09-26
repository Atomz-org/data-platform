---
title: MCX — All Commodities
---

What every commodity on the Multi Commodity Exchange settled in its latest session, and
what its trend, momentum, volatility and positioning say. One row per MCX contract code;
the flagship contract of each commodity is marked. Click a commodity for its own report.

**[Metrics by commodity →](/mcx/metrics)** — the semantic-layer scorecard: return, four
volatility estimators, roll yield, positioning and turnover over any window you pick.

Every figure is computed in the `mcx` marts (`rpt_mcx_commodity_board`); this page only
selects and sorts. Prices are ₹ per each contract's quote basis — GOLD per 10 g, SILVER
per kg, CRUDEOIL per barrel — so compare them only through returns and ratios.

```sql board
select
    mcx_commodity,
    upper(replace(mcx_commodity, '_', ' '))     as commodity_label,
    '/mcx/' || mcx_commodity                    as commodity_link,
    contract_code,
    contract_name,
    is_flagship,
    latest_trade_date,
    is_stale,
    close_price,
    quote_size || ' ' || quote_unit             as quote_basis,
    return_1d,
    return_21d,
    return_ytd,
    range_position_52w,
    rsi_14,
    trend_regime,
    realised_vol_20d,
    garman_klass_vol_30d,
    roll_yield_annualised                       as roll_yield,
    volatility_regime,
    oi_buildup,
    open_interest_change_pct,
    curve_state,
    annualised_carry,
    put_call_ratio_oi,
    premium_to_landed_pct,
    turnover_inr / 1e7                          as turnover_crore,
    stance
from commodity_india.rpt_mcx_commodity_board
order by mcx_commodity, is_flagship desc, turnover_inr desc
```

```sql headline
select
    count(distinct mcx_commodity)                         as commodities,
    count(*)                                              as contract_codes,
    max(latest_trade_date)                                as latest_session,
    sum(turnover_inr) / 1e7                               as turnover_crore,
    count(*) filter (where is_stale)                      as stale_codes
from commodity_india.rpt_mcx_commodity_board
```

<Grid cols=4>

<BigValue data={headline} value=commodities title='Commodities' fmt=num0/>
<BigValue data={headline} value=latest_session title='Latest session'/>
<BigValue data={headline} value=turnover_crore title='Futures turnover (₹ crore)' fmt=num0/>
<BigValue data={headline} value=stale_codes title='Codes behind the latest session' fmt=num0/>

</Grid>

```sql latest_metrics
select contract_code, garman_klass_vol_30d, ema_21, roll_yield_annualised, is_contango
from commodity_india.rpt_mcx_commodity_board
```

## Flagship contracts

One row per commodity — its benchmark-size contract. Returns are roll-free (inside one
contract), so a monthly roll never shows up as a move.

```sql flagships
select * from ${board} where is_flagship order by turnover_crore desc
```

<DataTable data={flagships} link=commodity_link rows=all>
    <Column id=mcx_commodity title='Commodity'/>
    <Column id=contract_code title='Code'/>
    <Column id=close_price title='Close' fmt='#,##0.00'/>
    <Column id=quote_basis title='Per'/>
    <Column id=return_1d title='1D' fmt=pct2 contentType=delta/>
    <Column id=return_21d title='1M' fmt=pct1 contentType=delta/>
    <Column id=return_ytd title='YTD' fmt=pct1 contentType=delta/>
    <Column id=range_position_52w title='52W position' fmt=pct0/>
    <Column id=rsi_14 title='RSI' fmt=num0/>
    <Column id=trend_regime title='Trend'/>
    <Column id=garman_klass_vol_30d title='GK vol 30d' fmt=pct0/>
    <Column id=roll_yield title='Roll yield' fmt=pct1 contentType=delta/>
    <Column id=oi_buildup title='OI read'/>
    <Column id=put_call_ratio_oi title='PCR' fmt=num2/>
    <Column id=premium_to_landed_pct title='vs landed' fmt=pct1 contentType=delta/>
    <Column id=turnover_crore title='Turnover ₹cr' fmt=num0/>
    <Column id=stance title='Stance'/>
</DataTable>

## One-month return, flagship contracts

```sql month_moves
select mcx_commodity, return_21d
from ${board}
where is_flagship and return_21d is not null
order by return_21d desc
```

<BarChart data={month_moves} x=mcx_commodity y=return_21d swapXY=true yFmt=pct1
    title='21-session return' sort=false/>

## Where the money traded

Turnover in the latest session, all expiries and all codes of each commodity. Turnover is
additive; prices are not.

```sql turnover
select mcx_commodity, sum(turnover_crore) as turnover_crore
from ${board}
group by mcx_commodity
order by turnover_crore desc
```

<BarChart data={turnover} x=mcx_commodity y=turnover_crore swapXY=true yFmt=num0
    title='Futures turnover, ₹ crore' sort=false/>

## Positioning

Price–open-interest read across every expiry: **long build-up** (price ↑ OI ↑), **short
build-up** (↓ ↑), **short covering** (↑ ↓), **long unwinding** (↓ ↓).

```sql positioning
select oi_buildup, count(*) as codes, string_agg(contract_code, ', ' order by contract_code) as contract_codes
from ${board}
where oi_buildup is not null
group by oi_buildup
order by codes desc
```

<DataTable data={positioning}/>

## Every contract code

```sql all_codes
select * from ${board}
```

<DataTable data={all_codes} link=commodity_link rows=40 search=true>
    <Column id=mcx_commodity title='Commodity'/>
    <Column id=contract_code title='Code'/>
    <Column id=contract_name title='Contract'/>
    <Column id=latest_trade_date title='Session'/>
    <Column id=close_price title='Close' fmt='#,##0.00'/>
    <Column id=quote_basis title='Per'/>
    <Column id=return_1d title='1D' fmt=pct2 contentType=delta/>
    <Column id=rsi_14 title='RSI' fmt=num0/>
    <Column id=curve_state title='Curve'/>
    <Column id=annualised_carry title='Carry (ann.)' fmt=pct1/>
    <Column id=stance title='Stance'/>
</DataTable>

## Every commodity at a glance

One section per commodity, for its flagship contract. Pick the window; everything below
filters in the browser.

```sql date_bounds
select min(trade_date) as trade_date from commodity_india.fct_mcx_commodity_daily
union all
select max(trade_date) from commodity_india.fct_mcx_commodity_daily
```

<DateRange name=window data={date_bounds} dates=trade_date defaultValue='Last 6 Months'/>

```sql flagship_series
select
    d.mcx_commodity,
    d.contract_code,
    d.trade_date,
    d.close_price,
    d.ema_9,
    d.ema_21,
    d.garman_klass_vol_30d,
    d.roll_yield_annualised
from commodity_india.fct_mcx_commodity_daily as d
where d.is_flagship
  and d.trade_date between '${inputs.window.start}' and '${inputs.window.end}'
order by d.trade_date
```

{#each flagships as c}

### {c.commodity_label} — {c.contract_code}

<Grid cols=4>
    <BigValue data={flagships.where(`contract_code = '${c.contract_code}'`)} value=close_price title='Settlement (₹)' fmt='#,##0.00'/>
    <BigValue data={board.where(`contract_code = '${c.contract_code}'`)} value=return_21d title='1-month return' fmt=pct1/>
    <BigValue data={latest_metrics.where(`contract_code = '${c.contract_code}'`)} value=garman_klass_vol_30d title='Garman–Klass vol, 30d' fmt=pct1/>
    <BigValue data={latest_metrics.where(`contract_code = '${c.contract_code}'`)} value=roll_yield_annualised title='Roll yield (ann.)' fmt=pct1/>
</Grid>

<LineChart data={flagship_series.where(`contract_code = '${c.contract_code}'`)} x=trade_date y={['close_price','ema_9','ema_21']} yFmt='#,##0' title='Settlement with EMA 9 and EMA 21 (₹)'/>

[Full {c.commodity_label} report →]({c.commodity_link})

{/each}

The stance is a legible rule, not a recommendation: the 50/200-session trend picks the
side, RSI and MACD pick the timing, open-interest build-up confirms it. `no_reading` means
a window is not yet full — fewer than 200 sessions of history for that code.
