---
title: US Import Parity
queries:
  - metrics/avg_benchmark_price_usd.sql
  - metrics/avg_usd_fx_rate.sql
  - metrics/avg_duty_local.sql
  - metrics/avg_landed_price_local.sql
---

How a benchmark becomes a US import-parity price for one commodity: the settlement price,
the rate it is converted at (one, for a USD market), and the duty grossed onto it. Pick a
commodity — the three inputs are on different scales and only compose within one.

```sql commodity_list
select distinct commodity_id, commodity_name
from commodity_us.rpt_commodity_price_board
where not is_import_prohibited
order by commodity_name
```

<Dropdown data={commodity_list} name=commodity value=commodity_id label=commodity_name defaultValue=gold title='Commodity'/>

```sql period_bounds
select min(metric_time) as metric_time from ${metrics_avg_landed_price_local}
union all
select max(metric_time) from ${metrics_avg_landed_price_local}
```

<DateRange name=period data={period_bounds} dates=metric_time/>

```sql headline
with benchmark as (
    select
        sum(benchmark_price_usd_total) as num,
        sum(benchmark_price_days)      as den
    from ${metrics_avg_benchmark_price_usd}
    where commodity_id = '${inputs.commodity.value}'
      and metric_time between '${inputs.period.start}' and '${inputs.period.end}'
),
fx as (
    select
        sum(usd_fx_rate_total) as num,
        sum(landed_price_days) as den
    from ${metrics_avg_usd_fx_rate}
    where commodity_id = '${inputs.commodity.value}'
      and metric_time between '${inputs.period.start}' and '${inputs.period.end}'
),
landed as (
    select
        sum(landed_price_local_total) as num,
        sum(landed_price_days)      as den
    from ${metrics_avg_landed_price_local}
    where commodity_id = '${inputs.commodity.value}'
      and metric_time between '${inputs.period.start}' and '${inputs.period.end}'
),
duty as (
    select
        sum(duty_local_total)    as num,
        sum(landed_price_days) as den
    from ${metrics_avg_duty_local}
    where commodity_id = '${inputs.commodity.value}'
      and metric_time between '${inputs.period.start}' and '${inputs.period.end}'
)
select
    benchmark.num / nullif(benchmark.den, 0) as benchmark_usd,
    fx.num       / nullif(fx.den, 0)         as fx_applied,
    duty.num     / nullif(duty.den, 0)       as duty_usd,
    landed.num   / nullif(landed.den, 0)     as landed_usd
from benchmark, fx, duty, landed
```

<Grid cols=4>

<BigValue data={headline} value=benchmark_usd title='Benchmark, USD per quote unit' fmt=num2/>
<BigValue data={headline} value=fx_applied title='FX applied (1 for USD)' fmt=num2/>
<BigValue data={headline} value=duty_usd title='Duty, USD per market unit' fmt=num0/>
<BigValue data={headline} value=landed_usd title='Import parity, USD per market unit' fmt=num0/>

</Grid>

Every figure above is a **ratio metric re-divided at this page's grain** — the carried
numerator over the carried denominator. Averaging the daily averages would weight a
thin trading week the same as a full one.

## Landed price over time

```sql landed_series
select
    metric_time,
    sum(landed_price_local_total) / nullif(sum(landed_price_days), 0) as landed_usd
from ${metrics_avg_landed_price_local}
where commodity_id = '${inputs.commodity.value}'
  and metric_time between '${inputs.period.start}' and '${inputs.period.end}'
group by 1
order by 1
```

<LineChart data={landed_series} x=metric_time y=landed_usd yFmt=num0 title='USD per market unit, import parity'/>

## The benchmark behind it

Shown separately rather than on a second axis: a USD-per-quote-unit price and an
USD-per-market-unit price share no scale, and putting them on one chart invents a
correlation the reader cannot check.

```sql benchmark_series
select
    metric_time,
    sum(benchmark_price_usd_total) / nullif(sum(benchmark_price_days), 0) as benchmark_usd
from ${metrics_avg_benchmark_price_usd}
where commodity_id = '${inputs.commodity.value}'
  and metric_time between '${inputs.period.start}' and '${inputs.period.end}'
group by 1
order by 1
```

<LineChart data={benchmark_series} x=metric_time y=benchmark_usd yFmt=num2 title='USD per quote unit, settlement'/>

## Monthly detail

```sql monthly
select
    date_trunc('month', metric_time)                                     as month,
    sum(landed_price_local_total) / nullif(sum(landed_price_days), 0)      as landed_usd,
    sum(landed_price_days)                                               as priced_days
from ${metrics_avg_landed_price_local}
where commodity_id = '${inputs.commodity.value}'
  and metric_time between '${inputs.period.start}' and '${inputs.period.end}'
group by 1
order by 1 desc
```

<DataTable data={monthly} rows=12>
    <Column id=month title='Month'/>
    <Column id=landed_usd title='Import parity (USD / market unit)' fmt=num0/>
    <Column id=priced_days title='Priced days' fmt=num0/>
</DataTable>

---

_Generated queries only: every number comes from `queries/metrics/`. The conversion and
duty logic lives in `fct_landed_prices_daily`; this page re-divides, it does not
recompute._
