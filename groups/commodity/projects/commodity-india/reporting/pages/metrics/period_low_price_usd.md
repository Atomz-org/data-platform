---
title: Period Low (USD)
queries:
  - metrics/period_low_price_usd.sql
---

Lowest traded price in the period, USD per quote unit. Group by commodity, **unfiltered** — every row in the underlying fact counts, measured over `price_date` from `fct_commodity_prices_daily`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, min(period_low_price_usd) as period_low_price_usd
from ${metrics_period_low_price_usd} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=period_low_price_usd yFmt=usd/>

## By commodity id

```sql by_dim
select commodity_id, min(period_low_price_usd) as period_low_price_usd
from ${metrics_period_low_price_usd} where commodity_id is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=commodity_id y=period_low_price_usd swapXY=true xFmt=usd/>

