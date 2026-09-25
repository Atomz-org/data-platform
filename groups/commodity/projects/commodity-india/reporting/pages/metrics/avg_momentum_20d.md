---
title: Avg 20-Day Momentum
queries:
  - metrics/avg_momentum_20d.sql
---

Mean 20-day rate of change. Group by commodity, **unfiltered** — every row in the underlying fact counts, measured over `price_date` from `fct_commodity_trading_signals_daily`, and carried as `momentum_20d_total` / `momentum_20d_days` so it re-divides correctly at any grain. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

> **Ratio metric.** Aggregated as `sum(momentum_20d_total) / sum(momentum_20d_days)` at whatever grain you group by. Averaging the ratio itself gives a different — and wrong — answer.

```sql series
select metric_time, sum(momentum_20d_total) as momentum_20d_total, sum(momentum_20d_days) as momentum_20d_days, sum(momentum_20d_total) / nullif(sum(momentum_20d_days), 0) as avg_momentum_20d
from ${metrics_avg_momentum_20d} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=avg_momentum_20d yFmt=num0/>

## By commodity id

```sql by_dim
select commodity_id, sum(momentum_20d_total) / nullif(sum(momentum_20d_days), 0) as avg_momentum_20d
from ${metrics_avg_momentum_20d} where commodity_id is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=commodity_id y=avg_momentum_20d swapXY=true xFmt=num0/>

