---
title: Avg Daily Return (flagship) — per Commodity
queries:
  - metrics/mcx_commodity_avg_daily_return.sql
---

The `mcx_commodity_avg_daily_return` metric, **unfiltered** — every row in the underlying fact counts, measured over `trade_date` from `fct_mcx_commodity_rollup_daily`, and carried as `mcx_commodity_return_total` / `mcx_commodity_return_days` so it re-divides correctly at any grain. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

> **Ratio metric.** Aggregated as `sum(mcx_commodity_return_total) / sum(mcx_commodity_return_days)` at whatever grain you group by. Averaging the ratio itself gives a different — and wrong — answer.

```sql series
select metric_time, sum(mcx_commodity_return_total) as mcx_commodity_return_total, sum(mcx_commodity_return_days) as mcx_commodity_return_days, sum(mcx_commodity_return_total) / nullif(sum(mcx_commodity_return_days), 0) as mcx_commodity_avg_daily_return
from ${metrics_mcx_commodity_avg_daily_return} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=mcx_commodity_avg_daily_return yFmt=pct2/>

## By mcx commodity

```sql by_dim
select mcx_commodity, sum(mcx_commodity_return_total) / nullif(sum(mcx_commodity_return_days), 0) as mcx_commodity_avg_daily_return
from ${metrics_mcx_commodity_avg_daily_return} where mcx_commodity is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=mcx_commodity y=mcx_commodity_avg_daily_return swapXY=true xFmt=pct2/>

