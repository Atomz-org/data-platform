---
title: MCX Metrics by Commodity
queries:
  - metrics/mcx_commodity_turnover_inr.sql
  - metrics/mcx_commodity_volume_flagship_lots.sql
  - metrics/mcx_commodity_oi_value_inr.sql
  - metrics/mcx_commodity_log_return.sql
  - metrics/mcx_commodity_hit_rate.sql
  - metrics/mcx_commodity_close_variance.sql
  - metrics/mcx_commodity_parkinson_variance.sql
  - metrics/mcx_commodity_gk_variance.sql
  - metrics/mcx_commodity_rs_variance.sql
  - metrics/mcx_commodity_avg_rsi.sql
  - metrics/mcx_commodity_avg_roll_yield.sql
  - metrics/mcx_commodity_contango_share.sql
  - metrics/mcx_commodity_put_call_ratio.sql
  - metrics/mcx_commodity_avg_premium_to_landed.sql
  - metrics/mcx_commodity_mini_turnover_share.sql
---

Every figure on this page is a metric from the dbt semantic layer (`mcx_commodities`,
`transform/models/marts/mcx/_mcx_commodities__semantic.yml`), compiled into
`queries/metrics/`. The page only picks a window and re-divides each ratio's own
components over it — `sum(numerator) / sum(denominator)`, never an average of daily
ratios.

How to read it:

- **One row per commodity.** Price and risk come from the flagship contract (GOLD, SILVER,
  CRUDEOIL, …). Turnover, open interest and options add up every contract code and
  expiry, in rupees.
- **Volatility.** The layer publishes annualised variance, and the page shows its square
  root. The MetricFlow metrics `mcx_commodity_*_vol` return the same numbers.
- **Period return.** Compounded from log returns: exp(Σ log r) − 1.
- **Open interest.** A stock, so it is read at the window's last session.

```sql date_bounds
select min(metric_time) as metric_time from ${metrics_mcx_commodity_turnover_inr}
union all
select max(metric_time) from ${metrics_mcx_commodity_turnover_inr}
```

```sql commodity_list
select mcx_commodity, sum(mcx_commodity_turnover_inr) as t
from ${metrics_mcx_commodity_turnover_inr}
group by 1 order by t desc
```

<DateRange name=window data={date_bounds} dates=metric_time defaultValue='Year to Date'/>
<Dropdown name=picked data={commodity_list} value=mcx_commodity multiple=true selectAllByDefault=true title='Commodities'/>

```sql scorecard
with w as (
    select '${inputs.window.start}'::date as d0, '${inputs.window.end}'::date as d1
),
activity as (
    select mcx_commodity, sum(mcx_commodity_turnover_inr) / 1e7 as turnover_crore
    from ${metrics_mcx_commodity_turnover_inr}, w
    where metric_time between d0 and d1 group by 1
),
lots as (
    select mcx_commodity, sum(mcx_commodity_volume_flagship_lots) as volume_lots
    from ${metrics_mcx_commodity_volume_flagship_lots}, w
    where metric_time between d0 and d1 group by 1
),
oi as (   -- a stock: the window's last session, per commodity
    select mcx_commodity, arg_max(mcx_commodity_oi_value_inr, metric_time) / 1e7 as oi_crore
    from ${metrics_mcx_commodity_oi_value_inr}, w
    where metric_time between d0 and d1 group by 1
),
ret as (
    select mcx_commodity, exp(sum(mcx_commodity_log_return)) - 1 as period_return
    from ${metrics_mcx_commodity_log_return}, w
    where metric_time between d0 and d1 group by 1
),
hit as (
    select mcx_commodity, sum(mcx_commodity_up_sessions) / nullif(sum(mcx_commodity_return_days), 0) as hit_rate
    from ${metrics_mcx_commodity_hit_rate}, w
    where metric_time between d0 and d1 group by 1
),
cc as (
    select mcx_commodity, sqrt(sum(mcx_commodity_close_var_total) / nullif(sum(mcx_commodity_close_var_days), 0)) as close_vol
    from ${metrics_mcx_commodity_close_variance}, w
    where metric_time between d0 and d1 group by 1
),
pk as (
    select mcx_commodity, sqrt(sum(mcx_commodity_parkinson_var_total) / nullif(sum(mcx_commodity_parkinson_var_days), 0)) as parkinson_vol
    from ${metrics_mcx_commodity_parkinson_variance}, w
    where metric_time between d0 and d1 group by 1
),
gk as (
    select mcx_commodity, sqrt(sum(mcx_commodity_gk_var_total) / nullif(sum(mcx_commodity_gk_var_days), 0)) as gk_vol
    from ${metrics_mcx_commodity_gk_variance}, w
    where metric_time between d0 and d1 group by 1
),
rs as (
    select mcx_commodity, sqrt(sum(mcx_commodity_rs_var_total) / nullif(sum(mcx_commodity_rs_var_days), 0)) as rs_vol
    from ${metrics_mcx_commodity_rs_variance}, w
    where metric_time between d0 and d1 group by 1
),
rsi as (
    select mcx_commodity, sum(mcx_commodity_rsi_total) / nullif(sum(mcx_commodity_rsi_days), 0) as avg_rsi
    from ${metrics_mcx_commodity_avg_rsi}, w
    where metric_time between d0 and d1 group by 1
),
roll as (
    select mcx_commodity, sum(mcx_commodity_roll_yield_total) / nullif(sum(mcx_commodity_roll_yield_days), 0) as roll_yield
    from ${metrics_mcx_commodity_avg_roll_yield}, w
    where metric_time between d0 and d1 group by 1
),
curve as (
    select mcx_commodity, sum(mcx_commodity_contango_sessions) / nullif(sum(mcx_commodity_sessions), 0) as contango_share
    from ${metrics_mcx_commodity_contango_share}, w
    where metric_time between d0 and d1 group by 1
),
pcr as (  -- positioning at the window's last session
    select mcx_commodity,
           arg_max(mcx_commodity_put_oi_notional_inr, metric_time)
             / nullif(arg_max(mcx_commodity_call_oi_notional_inr, metric_time), 0) as put_call_ratio
    from ${metrics_mcx_commodity_put_call_ratio}, w
    where metric_time between d0 and d1 group by 1
),
parity as (
    select mcx_commodity, sum(mcx_commodity_premium_total) / nullif(sum(mcx_commodity_premium_days), 0) as premium_to_landed
    from ${metrics_mcx_commodity_avg_premium_to_landed}, w
    where metric_time between d0 and d1 group by 1
),
minis as (
    select mcx_commodity, sum(mcx_commodity_mini_turnover_inr) / nullif(sum(mcx_commodity_turnover_inr), 0) as mini_share
    from ${metrics_mcx_commodity_mini_turnover_share}, w
    where metric_time between d0 and d1 group by 1
)
select
    a.mcx_commodity,
    '/mcx/' || a.mcx_commodity as commodity_link,
    a.turnover_crore, l.volume_lots, oi.oi_crore,
    ret.period_return, hit.hit_rate,
    cc.close_vol, pk.parkinson_vol, gk.gk_vol, rs.rs_vol,
    rsi.avg_rsi, roll.roll_yield, curve.contango_share,
    pcr.put_call_ratio, parity.premium_to_landed, minis.mini_share
from activity a
left join lots l using (mcx_commodity)
left join oi using (mcx_commodity)
left join ret using (mcx_commodity)
left join hit using (mcx_commodity)
left join cc using (mcx_commodity)
left join pk using (mcx_commodity)
left join gk using (mcx_commodity)
left join rs using (mcx_commodity)
left join rsi using (mcx_commodity)
left join roll using (mcx_commodity)
left join curve using (mcx_commodity)
left join pcr using (mcx_commodity)
left join parity using (mcx_commodity)
left join minis using (mcx_commodity)
where a.mcx_commodity in ${inputs.picked.value}
order by a.turnover_crore desc
```

```sql totals
select sum(turnover_crore) as turnover_crore, sum(oi_crore) as oi_crore, count(*) as commodities
from ${scorecard}
```

<Grid cols=3>
<BigValue data={totals} value=turnover_crore title='Futures turnover in window (₹ crore)' fmt=num0/>
<BigValue data={totals} value=oi_crore title='Open interest at window end (₹ crore)' fmt=num0/>
<BigValue data={totals} value=commodities title='Commodities selected' fmt=num0/>
</Grid>

## Scorecard

<DataTable data={scorecard} link=commodity_link rows=all>
    <Column id=mcx_commodity title='Commodity'/>
    <Column id=turnover_crore title='Turnover ₹cr' fmt=num0/>
    <Column id=volume_lots title='Volume (flagship lots)' fmt=num0/>
    <Column id=oi_crore title='OI ₹cr (last)' fmt=num0/>
    <Column id=period_return title='Return' fmt=pct1 contentType=delta/>
    <Column id=hit_rate title='Up sessions' fmt=pct0/>
    <Column id=close_vol title='Vol C-C' fmt=pct0/>
    <Column id=gk_vol title='Vol GK' fmt=pct0/>
    <Column id=avg_rsi title='Avg RSI' fmt=num0/>
    <Column id=roll_yield title='Roll yield' fmt=pct1 contentType=delta/>
    <Column id=contango_share title='In contango' fmt=pct0/>
    <Column id=put_call_ratio title='PCR' fmt=num2/>
    <Column id=premium_to_landed title='vs landed' fmt=pct1 contentType=delta/>
    <Column id=mini_share title='Mini share' fmt=pct0/>
</DataTable>

## Return over the window

```sql returns_sorted
select mcx_commodity, period_return from ${scorecard} where period_return is not null order by period_return desc
```

<BarChart data={returns_sorted} x=mcx_commodity y=period_return swapXY=true yFmt=pct1 sort=false title='Flagship return, compounded'/>

## Four views of risk

Close-to-close sees every move, overnight gaps included. The three range estimators read
the session's own open, high and low, and miss what happens between sessions. When
close-to-close sits well above Garman–Klass, the risk came overnight.

Commodities with under 1,000 flagship lots traded in the window are left out of the chart.
A handful of trades makes a range estimator print noise (kapas reads over 60% on four
lots). They stay in the table below, flagged.

```sql liquid
select * from ${scorecard} where volume_lots >= 1000
```

```sql vols
select mcx_commodity, 'Close-to-close' as estimator, close_vol as vol from ${liquid}
union all select mcx_commodity, 'Parkinson', parkinson_vol from ${liquid}
union all select mcx_commodity, 'Garman–Klass', gk_vol from ${liquid}
union all select mcx_commodity, 'Rogers–Satchell', rs_vol from ${liquid}
```

<BarChart data={vols} x=mcx_commodity y=vol series=estimator type=grouped yFmt=pct0
    seriesOrder={['Close-to-close','Parkinson','Garman–Klass','Rogers–Satchell']}
    title='Annualised volatility over the window (liquid commodities)'/>

```sql vol_table
select *, volume_lots < 1000 as is_thin from ${scorecard}
```

<DataTable data={vol_table} rows=all>
    <Column id=mcx_commodity title='Commodity'/>
    <Column id=close_vol title='Close-to-close' fmt=pct1/>
    <Column id=parkinson_vol title='Parkinson' fmt=pct1/>
    <Column id=gk_vol title='Garman–Klass' fmt=pct1/>
    <Column id=rs_vol title='Rogers–Satchell' fmt=pct1/>
    <Column id=is_thin title='Thin (< 1,000 lots)'/>
</DataTable>

## The curve: what a long pays to hold

```sql roll_sorted
select mcx_commodity, roll_yield from ${scorecard} where roll_yield is not null order by roll_yield
```

<BarChart data={roll_sorted} x=mcx_commodity y=roll_yield swapXY=true yFmt=pct1 sort=false title='Average annualised roll yield (negative = contango)'/>

## Where the money traded, month by month

```sql monthly_turnover
select date_trunc('month', metric_time) as month, mcx_commodity,
       sum(mcx_commodity_turnover_inr) / 1e7 as turnover_crore
from ${metrics_mcx_commodity_turnover_inr}
where metric_time between '${inputs.window.start}' and '${inputs.window.end}'
  and mcx_commodity in (select mcx_commodity from ${scorecard} order by turnover_crore desc limit 4)
group by 1, 2 order by 1
```

<LineChart data={monthly_turnover} x=month y=turnover_crore series=mcx_commodity yFmt=num0 title='Monthly futures turnover, four largest commodities (₹ crore)'/>

## Volatility regime, month by month

```sql monthly_gk
select date_trunc('month', metric_time) as month, mcx_commodity,
       sqrt(sum(mcx_commodity_gk_var_total) / nullif(sum(mcx_commodity_gk_var_days), 0)) as gk_vol
from ${metrics_mcx_commodity_gk_variance}
where metric_time between '${inputs.window.start}' and '${inputs.window.end}'
  and mcx_commodity in (select mcx_commodity from ${scorecard} order by turnover_crore desc limit 4)
group by 1, 2 order by 1
```

<LineChart data={monthly_gk} x=month y=gk_vol series=mcx_commodity yFmt=pct0 title='Garman–Klass volatility per month, four largest commodities'/>

[← MCX summary](/mcx)
