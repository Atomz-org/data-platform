---
title: 20-Day Momentum (component)
queries:
  - metrics/momentum_20d_total.sql
---

The `momentum_20d_total` metric, **unfiltered** — every row in the underlying fact counts, measured over `price_date` from `fct_commodity_trading_signals_daily`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(momentum_20d_total) as momentum_20d_total
from ${metrics_momentum_20d_total} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=momentum_20d_total yFmt=num0/>

## By commodity id

```sql by_dim
select commodity_id, sum(momentum_20d_total) as momentum_20d_total
from ${metrics_momentum_20d_total} where commodity_id is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=commodity_id y=momentum_20d_total swapXY=true xFmt=num0/>

