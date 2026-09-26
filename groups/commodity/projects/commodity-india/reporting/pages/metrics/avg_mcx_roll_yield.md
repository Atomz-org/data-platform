---
title: Avg MCX Roll Yield (annualised)
queries:
  - metrics/avg_mcx_roll_yield.sql
---

What a long earns rolling the near month into the next, annualised — negative in contango, positive in backwardation. Group by contract_code.
, **unfiltered** — every row in the underlying fact counts, measured over `trade_date` from `fct_mcx_commodity_daily`, and carried as `mcx_roll_yield_total` / `mcx_roll_yield_days` so it re-divides correctly at any grain. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

> **Ratio metric.** Aggregated as `sum(mcx_roll_yield_total) / sum(mcx_roll_yield_days)` at whatever grain you group by. Averaging the ratio itself gives a different — and wrong — answer.

```sql series
select metric_time, sum(mcx_roll_yield_total) as mcx_roll_yield_total, sum(mcx_roll_yield_days) as mcx_roll_yield_days, sum(mcx_roll_yield_total) / nullif(sum(mcx_roll_yield_days), 0) as avg_mcx_roll_yield
from ${metrics_avg_mcx_roll_yield} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=avg_mcx_roll_yield yFmt=pct1/>

## By contract code

```sql by_dim
select contract_code, sum(mcx_roll_yield_total) / nullif(sum(mcx_roll_yield_days), 0) as avg_mcx_roll_yield
from ${metrics_avg_mcx_roll_yield} where contract_code is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=contract_code y=avg_mcx_roll_yield swapXY=true xFmt=pct1/>

