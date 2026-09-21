---
title: Period High (USD)
queries:
  - metrics/period_high_price_usd.sql
---

Highest traded price in the period, USD per quote unit. Group by commodity, **unfiltered** — every row in the underlying fact counts, measured over `price_date` from `fct_commodity_prices_daily`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, max(period_high_price_usd) as period_high_price_usd
from ${metrics_period_high_price_usd} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=period_high_price_usd yFmt=num0/>

## By commodity id

```sql by_dim
select commodity_id, max(period_high_price_usd) as period_high_price_usd
from ${metrics_period_high_price_usd} where commodity_id is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=commodity_id y=period_high_price_usd swapXY=true xFmt=num0/>

