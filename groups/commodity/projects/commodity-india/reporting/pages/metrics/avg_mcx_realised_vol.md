---
title: Avg MCX Realised Volatility (annualised)
queries:
  - metrics/avg_mcx_realised_vol.sql
---

20-session close-to-close dispersion annualised on 252 sessions. Group by contract_code, **unfiltered** — every row in the underlying fact counts, measured over `trade_date` from `fct_mcx_commodity_daily`, and carried as `mcx_realised_vol_total` / `mcx_realised_vol_days` so it re-divides correctly at any grain. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

> **Ratio metric.** Aggregated as `sum(mcx_realised_vol_total) / sum(mcx_realised_vol_days)` at whatever grain you group by. Averaging the ratio itself gives a different — and wrong — answer.

```sql series
select metric_time, sum(mcx_realised_vol_total) as mcx_realised_vol_total, sum(mcx_realised_vol_days) as mcx_realised_vol_days, sum(mcx_realised_vol_total) / nullif(sum(mcx_realised_vol_days), 0) as avg_mcx_realised_vol
from ${metrics_avg_mcx_realised_vol} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=avg_mcx_realised_vol yFmt=pct1/>

## By contract code

```sql by_dim
select contract_code, sum(mcx_realised_vol_total) / nullif(sum(mcx_realised_vol_days), 0) as avg_mcx_realised_vol
from ${metrics_avg_mcx_realised_vol} where contract_code is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=contract_code y=avg_mcx_realised_vol swapXY=true xFmt=pct1/>

