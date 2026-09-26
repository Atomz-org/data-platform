---
title: Avg MCX Daily Return
queries:
  - metrics/avg_mcx_daily_return.sql
---

Mean roll-free daily return of the most-active contract. Group by contract_code, **unfiltered** — every row in the underlying fact counts, measured over `trade_date` from `fct_mcx_commodity_daily`, and carried as `mcx_return_total` / `mcx_session_days` so it re-divides correctly at any grain. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

> **Ratio metric.** Aggregated as `sum(mcx_return_total) / sum(mcx_session_days)` at whatever grain you group by. Averaging the ratio itself gives a different — and wrong — answer.

```sql series
select metric_time, sum(mcx_return_total) as mcx_return_total, sum(mcx_session_days) as mcx_session_days, sum(mcx_return_total) / nullif(sum(mcx_session_days), 0) as avg_mcx_daily_return
from ${metrics_avg_mcx_daily_return} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=avg_mcx_daily_return yFmt=pct2/>

## By contract code

```sql by_dim
select contract_code, sum(mcx_return_total) / nullif(sum(mcx_session_days), 0) as avg_mcx_daily_return
from ${metrics_avg_mcx_daily_return} where contract_code is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=contract_code y=avg_mcx_daily_return swapXY=true xFmt=pct2/>

