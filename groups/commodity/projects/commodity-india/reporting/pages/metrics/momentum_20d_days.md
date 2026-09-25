---
title: Days With a Momentum Reading
queries:
  - metrics/momentum_20d_days.sql
---

The `momentum_20d_days` metric, **unfiltered** — every row in the underlying fact counts, measured over `price_date` from `fct_commodity_trading_signals_daily`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(momentum_20d_days) as momentum_20d_days
from ${metrics_momentum_20d_days} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=momentum_20d_days yFmt=num0/>

## By commodity id

```sql by_dim
select commodity_id, sum(momentum_20d_days) as momentum_20d_days
from ${metrics_momentum_20d_days} where commodity_id is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=commodity_id y=momentum_20d_days swapXY=true xFmt=num0/>

