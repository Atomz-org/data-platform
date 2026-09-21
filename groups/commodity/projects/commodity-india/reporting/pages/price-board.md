---
title: Commodity Price Board
---

Which of the tracked benchmarks can be quoted this morning, and which are running on a
carried-forward indicative level. A commodity with **stale** against it is the last level
we received, not today's market — quote it and you are quoting June.

```sql freshness
select
    count(*)                                          as tracked,
    count(*) filter (where not is_stale)              as quotable,
    count(*) filter (where is_stale)                  as stale,
    max(price_date)                                   as latest_price_date
from commodity_india.rpt_commodity_price_board
```

<Grid cols=4>

<BigValue data={freshness} value=quotable title='Quotable today' fmt=num0/>
<BigValue data={freshness} value=stale title='Running on a stale level' fmt=num0/>
<BigValue data={freshness} value=tracked title='Benchmarks tracked' fmt=num0/>
<BigValue data={freshness} value=latest_price_date title='Latest price date'/>

</Grid>

## Where the staleness sits

Staleness is not spread evenly. The industrial metals have no free live feed, so they hold
the last indicative LME level until `indicative_prices` is refreshed; agri and precious
arrive daily. Read this chart before assuming a gap is a data incident.

```sql category_freshness
select
    category,
    count(*) filter (where not is_stale) as quotable,
    count(*) filter (where is_stale)     as stale
from commodity_india.rpt_commodity_price_board
group by 1
order by stale desc, category
```

<BarChart
    data={category_freshness}
    x=category
    y={['quotable','stale']}
    type=stacked
    swapXY=true
    title='Quotable vs stale benchmarks, by category'
    xFmt=num0
    labels=true
/>

## Today's movers

Day-on-day change on the benchmark settlement, quotable commodities only. Prices are
**not additive** — each bar is one commodity's own percentage move, never a total across
them.

```sql movers
select
    commodity_name,
    price_change_pct
from commodity_india.rpt_commodity_price_board
where not is_stale and price_change_pct is not null
order by abs(price_change_pct) desc
limit 12
```

<BarChart
    data={movers}
    x=commodity_name
    y=price_change_pct
    swapXY=true
    title='Largest day-on-day moves'
    xFmt=pct1
    labels=true
/>

## The board

`landed_price_local` is the benchmark converted at the day's USD/INR and grossed up by the
effective customs duty. It is blank where import is prohibited, and it inherits the
staleness of the benchmark behind it.

```sql board
select
    commodity_name,
    category,
    segment,
    price_date,
    benchmark_price_usd,
    quote_unit,
    price_change_pct,
    usd_fx_rate,
    effective_duty_rate,
    landed_price_local,
    market_unit,
    price_age_days,
    is_stale,
    is_import_prohibited,
    is_duty_rate_confirmed
from commodity_india.rpt_commodity_price_board
order by is_stale desc, category, commodity_name
```

<DataTable data={board} rows=20 search=true>
    <Column id=commodity_name title='Commodity'/>
    <Column id=category title='Category'/>
    <Column id=price_date title='Priced'/>
    <Column id=price_age_days title='Age (d)' fmt=num0 contentType=colorscale/>
    <Column id=benchmark_price_usd title='Benchmark (USD)' fmt=num2/>
    <Column id=quote_unit title='Per'/>
    <Column id=price_change_pct title='Day' fmt=pct1 contentType=delta/>
    <Column id=usd_fx_rate title='USD/INR' fmt=num2/>
    <Column id=effective_duty_rate title='Duty' fmt=pct1/>
    <Column id=landed_price_local title='Landed (INR)' fmt=num2/>
    <Column id=market_unit title='Per'/>
    <Column id=is_import_prohibited title='Import banned'/>
    <Column id=is_duty_rate_confirmed title='Duty confirmed'/>
</DataTable>

---

_Source: `rpt_commodity_price_board`, one row per tracked commodity. Business logic lives
in the mart; this page selects and formats it. A number you need that is not here is a dbt
change, not SQL in this file._
