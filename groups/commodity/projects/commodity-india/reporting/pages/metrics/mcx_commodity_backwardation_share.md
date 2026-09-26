---
title: Share of Sessions in Backwardation — per Commodity
queries:
  - metrics/mcx_commodity_backwardation_share.sql
---

The `mcx_commodity_backwardation_share` metric, **unfiltered** — every row in the underlying fact counts, measured over `trade_date` from `fct_mcx_commodity_rollup_daily`, and carried as `mcx_commodity_backwardation_sessions` / `mcx_commodity_sessions` so it re-divides correctly at any grain. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

> **Ratio metric.** Aggregated as `sum(mcx_commodity_backwardation_sessions) / sum(mcx_commodity_sessions)` at whatever grain you group by. Averaging the ratio itself gives a different — and wrong — answer.

```sql series
select metric_time, sum(mcx_commodity_backwardation_sessions) as mcx_commodity_backwardation_sessions, sum(mcx_commodity_sessions) as mcx_commodity_sessions, sum(mcx_commodity_backwardation_sessions) / nullif(sum(mcx_commodity_sessions), 0) as mcx_commodity_backwardation_share
from ${metrics_mcx_commodity_backwardation_share} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=mcx_commodity_backwardation_share yFmt=pct1/>

## By mcx commodity

```sql by_dim
select mcx_commodity, sum(mcx_commodity_backwardation_sessions) / nullif(sum(mcx_commodity_sessions), 0) as mcx_commodity_backwardation_share
from ${metrics_mcx_commodity_backwardation_share} where mcx_commodity is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=mcx_commodity y=mcx_commodity_backwardation_share swapXY=true xFmt=pct1/>

