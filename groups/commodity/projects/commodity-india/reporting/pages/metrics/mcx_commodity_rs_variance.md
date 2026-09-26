---
title: Rogers–Satchell Variance (annualised) — per Commodity
queries:
  - metrics/mcx_commodity_rs_variance.sql
---

Rogers–Satchell (1991) drift-robust OHLC variance per session, × 252. Prefer it to Garman–Klass in a trending market, **unfiltered** — every row in the underlying fact counts, measured over `trade_date` from `fct_mcx_commodity_rollup_daily`, and carried as `mcx_commodity_rs_var_total` / `mcx_commodity_rs_var_days` so it re-divides correctly at any grain. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

> **Ratio metric.** Aggregated as `sum(mcx_commodity_rs_var_total) / sum(mcx_commodity_rs_var_days)` at whatever grain you group by. Averaging the ratio itself gives a different — and wrong — answer.

```sql series
select metric_time, sum(mcx_commodity_rs_var_total) as mcx_commodity_rs_var_total, sum(mcx_commodity_rs_var_days) as mcx_commodity_rs_var_days, sum(mcx_commodity_rs_var_total) / nullif(sum(mcx_commodity_rs_var_days), 0) as mcx_commodity_rs_variance
from ${metrics_mcx_commodity_rs_variance} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=mcx_commodity_rs_variance yFmt=num3/>

## By mcx commodity

```sql by_dim
select mcx_commodity, sum(mcx_commodity_rs_var_total) / nullif(sum(mcx_commodity_rs_var_days), 0) as mcx_commodity_rs_variance
from ${metrics_mcx_commodity_rs_variance} where mcx_commodity is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=mcx_commodity y=mcx_commodity_rs_variance swapXY=true xFmt=num3/>

