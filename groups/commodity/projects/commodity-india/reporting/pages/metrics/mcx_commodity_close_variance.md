---
title: Realised Variance, Close-to-Close (annualised) — per Commodity
queries:
  - metrics/mcx_commodity_close_variance.sql
---

Zero-mean realised variance of the flagship's daily log returns, × 252. Its square root is realised volatility over whatever window the query asks for, **unfiltered** — every row in the underlying fact counts, measured over `trade_date` from `fct_mcx_commodity_rollup_daily`, and carried as `mcx_commodity_close_var_total` / `mcx_commodity_close_var_days` so it re-divides correctly at any grain. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

> **Ratio metric.** Aggregated as `sum(mcx_commodity_close_var_total) / sum(mcx_commodity_close_var_days)` at whatever grain you group by. Averaging the ratio itself gives a different — and wrong — answer.

```sql series
select metric_time, sum(mcx_commodity_close_var_total) as mcx_commodity_close_var_total, sum(mcx_commodity_close_var_days) as mcx_commodity_close_var_days, sum(mcx_commodity_close_var_total) / nullif(sum(mcx_commodity_close_var_days), 0) as mcx_commodity_close_variance
from ${metrics_mcx_commodity_close_variance} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=mcx_commodity_close_variance yFmt=num3/>

## By mcx commodity

```sql by_dim
select mcx_commodity, sum(mcx_commodity_close_var_total) / nullif(sum(mcx_commodity_close_var_days), 0) as mcx_commodity_close_variance
from ${metrics_mcx_commodity_close_variance} where mcx_commodity is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=mcx_commodity y=mcx_commodity_close_variance swapXY=true xFmt=num3/>

