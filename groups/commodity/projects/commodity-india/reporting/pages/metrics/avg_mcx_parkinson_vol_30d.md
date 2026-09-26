---
title: Avg MCX Parkinson Volatility, 30 sessions (annualised)
queries:
  - metrics/avg_mcx_parkinson_vol_30d.sql
---

High–low range estimator over 30 sessions, annualised on 252. Group by contract_code, **unfiltered** — every row in the underlying fact counts, measured over `trade_date` from `fct_mcx_commodity_daily`, and carried as `mcx_parkinson_vol_30d_total` / `mcx_parkinson_vol_30d_days` so it re-divides correctly at any grain. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

> **Ratio metric.** Aggregated as `sum(mcx_parkinson_vol_30d_total) / sum(mcx_parkinson_vol_30d_days)` at whatever grain you group by. Averaging the ratio itself gives a different — and wrong — answer.

```sql series
select metric_time, sum(mcx_parkinson_vol_30d_total) as mcx_parkinson_vol_30d_total, sum(mcx_parkinson_vol_30d_days) as mcx_parkinson_vol_30d_days, sum(mcx_parkinson_vol_30d_total) / nullif(sum(mcx_parkinson_vol_30d_days), 0) as avg_mcx_parkinson_vol_30d
from ${metrics_avg_mcx_parkinson_vol_30d} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=avg_mcx_parkinson_vol_30d yFmt=pct1/>

## By contract code

```sql by_dim
select contract_code, sum(mcx_parkinson_vol_30d_total) / nullif(sum(mcx_parkinson_vol_30d_days), 0) as avg_mcx_parkinson_vol_30d
from ${metrics_avg_mcx_parkinson_vol_30d} where contract_code is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=contract_code y=avg_mcx_parkinson_vol_30d swapXY=true xFmt=pct1/>

