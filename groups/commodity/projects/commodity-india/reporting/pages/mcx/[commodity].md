---
title: MCX Commodity Report
---

```sql codes
select
    contract_code,
    contract_name,
    upper(replace(mcx_commodity, '_', ' '))     as commodity_label,
    is_flagship,
    close_price,
    quote_size || ' ' || quote_unit             as quote_basis,
    lot_size || ' ' || lot_unit                 as lot,
    notional_per_lot_inr,
    return_1d,
    return_5d,
    return_21d,
    return_63d,
    return_252d,
    return_ytd,
    latest_trade_date,
    is_stale,
    stance
from commodity_india.rpt_mcx_commodity_board
where mcx_commodity = '${params.commodity}'
order by is_flagship desc, contract_code
```

# MCX {codes[0]?.commodity_label ?? params.commodity}

Every number here comes from the `mcx` marts; the page filters them to one commodity.
Prices are ₹ per the contract's quote basis. Indicators run on a roll-free, back-adjusted
series of the most-active contract (highest open interest), so a monthly roll is never a
signal.

<Dropdown data={codes} name=code value=contract_code title='Contract' defaultValue={codes[0].contract_code}/>

```sql head
select *
from commodity_india.rpt_mcx_commodity_board
where contract_code = '${inputs.code.value}'
```

<Grid cols=5>

<BigValue data={head} value=close_price title='Settlement (₹)' fmt='#,##0.00'/>
<BigValue data={head} value=return_1d title='1-day' fmt=pct2/>
<BigValue data={head} value=return_ytd title='Year to date' fmt=pct1/>
<BigValue data={head} value=rsi_14 title='RSI(14)' fmt=num0/>
<BigValue data={head} value=stance title='Stance'/>

</Grid>

<Grid cols=5>

<BigValue data={head} value=garman_klass_vol_30d title='Garman–Klass vol, 30d' fmt=pct0/>
<BigValue data={head} value=atr_14 title='ATR(14) ₹' fmt='#,##0.00'/>
<BigValue data={head} value=range_position_52w title='In 52-week range' fmt=pct0/>
<BigValue data={head} value=roll_yield_annualised title='Roll yield (ann.)' fmt=pct1/>
<BigValue data={head} value=premium_to_landed_pct title='vs landed parity' fmt=pct1/>

</Grid>

## Contracts of this commodity

<DataTable data={codes} rows=all>
    <Column id=contract_code title='Code'/>
    <Column id=contract_name title='Contract'/>
    <Column id=close_price title='Close' fmt='#,##0.00'/>
    <Column id=quote_basis title='Per'/>
    <Column id=lot title='Lot'/>
    <Column id=notional_per_lot_inr title='₹ per lot' fmt=num0/>
    <Column id=return_1d title='1D' fmt=pct2 contentType=delta/>
    <Column id=return_5d title='1W' fmt=pct1 contentType=delta/>
    <Column id=return_21d title='1M' fmt=pct1 contentType=delta/>
    <Column id=return_63d title='3M' fmt=pct1 contentType=delta/>
    <Column id=return_252d title='1Y' fmt=pct1 contentType=delta/>
    <Column id=stance title='Stance'/>
</DataTable>

```sql daily
select
    trade_date,
    close_price,
    sma_50,
    sma_200,
    bollinger_upper,
    bollinger_lower,
    rsi_14,
    macd_histogram_pct,
    ema_9,
    ema_21,
    ema_200,
    cumulative_return,
    close_vol_30d,
    parkinson_vol_30d,
    garman_klass_vol_30d,
    rogers_satchell_vol_30d,
    roll_yield_annualised,
    volume_lots,
    open_interest_lots,
    oi_buildup,
    open_interest_change_pct,
    calendar_spread,
    annualised_carry,
    rollover_pct,
    premium_to_landed_pct,
    is_roll_day,
    stance
from commodity_india.fct_mcx_commodity_daily
where contract_code = '${inputs.code.value}'
order by trade_date
```

## Price and trend

Settlement of the most-active contract with its 50- and 200-session averages.

<LineChart data={daily} x=trade_date y={['close_price','sma_50','sma_200']} yFmt='#,##0' title='Settlement, SMA 50, SMA 200 (₹)'/>

<LineChart data={daily} x=trade_date y={['close_price','ema_9','ema_21']} yFmt='#,##0' title='Settlement with EMA 9 and EMA 21 — the fast momentum crossover'/>

<LineChart data={daily} x=trade_date y=cumulative_return yFmt=pct0 title='Cumulative return since the first session (roll-free)'/>

<LineChart data={daily} x=trade_date y={['close_price','bollinger_upper','bollinger_lower']} yFmt='#,##0' title='Bollinger bands (20, 2)'/>

## Momentum

<LineChart data={daily} x=trade_date y=rsi_14 yMin=0 yMax=100 title='RSI(14)'>
    <ReferenceLine y=70 label='Overbought'/>
    <ReferenceLine y=30 label='Oversold'/>
</LineChart>

<BarChart data={daily} x=trade_date y=macd_histogram_pct yFmt=pct2 title='MACD histogram, share of price'/>

## Volatility

Four estimators over 30 sessions, annualised. The range estimators use the session's open,
high and low as well as its close; when they sit well above close-to-close, the market swung
further intraday than it ended up moving.

<LineChart data={daily} x=trade_date y={['close_vol_30d','parkinson_vol_30d','garman_klass_vol_30d','rogers_satchell_vol_30d']} yFmt=pct0 title='30-session volatility: close-to-close, Parkinson, Garman–Klass, Rogers–Satchell'/>

## Activity and positioning

Volume and open interest are in lots across every open expiry — two charts, because they
are two scales.

<BarChart data={daily} x=trade_date y=volume_lots yFmt=num0 title='Volume (lots)'/>

<LineChart data={daily} x=trade_date y=open_interest_lots yFmt=num0 title='Open interest (lots)'/>

```sql recent
select trade_date, close_price, open_interest_change_pct, oi_buildup, rollover_pct, is_roll_day, stance
from ${daily}
order by trade_date desc
limit 20
```

<DataTable data={recent} rows=20 title='Last 20 sessions'>
    <Column id=trade_date title='Session'/>
    <Column id=close_price title='Close' fmt='#,##0.00'/>
    <Column id=open_interest_change_pct title='OI change' fmt=pct1 contentType=delta/>
    <Column id=oi_buildup title='OI read'/>
    <Column id=rollover_pct title='In later expiries' fmt=pct0/>
    <Column id=is_roll_day title='Roll day'/>
    <Column id=stance title='Stance'/>
</DataTable>

## The curve

```sql curve
select expiry_date, close_price, open_interest_lots, volume_lots, days_to_expiry, oi_buildup
from commodity_india.fct_mcx_futures_daily
where contract_code = '${inputs.code.value}'
  and trade_date = (select max(trade_date) from commodity_india.fct_mcx_futures_daily
                    where contract_code = '${inputs.code.value}')
order by expiry_date
```

<LineChart data={curve} x=expiry_date y=close_price yFmt='#,##0' markers=true title='Term structure, latest session'/>

<DataTable data={curve} rows=all>
    <Column id=expiry_date title='Expiry'/>
    <Column id=days_to_expiry title='Days left'/>
    <Column id=close_price title='Close' fmt='#,##0.00'/>
    <Column id=volume_lots title='Volume' fmt=num0/>
    <Column id=open_interest_lots title='OI' fmt=num0/>
    <Column id=oi_buildup title='OI read'/>
</DataTable>

<LineChart data={daily} x=trade_date y=roll_yield_annualised yFmt=pct1 title='Roll yield to a long, annualised (negative = contango)'/>

```sql parity
select trade_date, premium_to_landed_pct from ${daily} where premium_to_landed_pct is not null
```

{#if parity.length > 0}

<LineChart data={parity} x=trade_date y=premium_to_landed_pct yFmt=pct1 title='MCX premium to landed import parity'/>

{/if}

## Options

```sql chains
select trade_date, expiry_date, put_call_ratio_oi, put_call_ratio_volume, positioning,
       max_pain_strike, call_wall_strike, put_wall_strike, underlying_close_price,
       max_pain_distance_pct, call_open_interest_lots, put_open_interest_lots, expiry_rank
from commodity_india.fct_mcx_options_daily
where contract_code = '${inputs.code.value}'
order by trade_date, expiry_date
```

{#if chains.length > 0}

```sql near_chain
select * from ${chains} where expiry_rank = 1 order by trade_date
```

<LineChart data={near_chain} x=trade_date y=put_call_ratio_oi yFmt=num2 title='Put/call ratio by open interest, nearest expiry'/>

```sql latest_chains
select * from ${chains} where trade_date = (select max(trade_date) from ${chains}) order by expiry_date
```

<DataTable data={latest_chains} rows=all title='Option chains, latest session'>
    <Column id=expiry_date title='Expiry'/>
    <Column id=underlying_close_price title='Underlying' fmt='#,##0'/>
    <Column id=max_pain_strike title='Max pain' fmt='#,##0'/>
    <Column id=max_pain_distance_pct title='Max pain vs spot' fmt=pct1 contentType=delta/>
    <Column id=call_wall_strike title='Call wall' fmt='#,##0'/>
    <Column id=put_wall_strike title='Put wall' fmt='#,##0'/>
    <Column id=put_call_ratio_oi title='PCR (OI)' fmt=num2/>
    <Column id=put_call_ratio_volume title='PCR (vol)' fmt=num2/>
    <Column id=positioning title='Positioning'/>
</DataTable>

{:else}

MCX lists no options on {inputs.code.value}, or none in the options history window.

{/if}

## Expiry calendar

```sql expiries
select contract_code, contract_kind, expiry_date, days_to_expiry, is_traded_today
from commodity_india.dim_mcx_contracts
where mcx_commodity = '${params.commodity}' and is_open
order by expiry_date, contract_code
```

<DataTable data={expiries} rows=15>
    <Column id=contract_code title='Code'/>
    <Column id=contract_kind title='Kind'/>
    <Column id=expiry_date title='Expiry'/>
    <Column id=days_to_expiry title='Days left'/>
    <Column id=is_traded_today title='Traded last session'/>
</DataTable>

[← All MCX commodities](/mcx)
