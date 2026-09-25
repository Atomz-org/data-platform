---
title: Avg Realised Volatility (annualised)
queries:
  - metrics/avg_realised_vol.sql
---

20-day dispersion annualised on 252 trading days. Group by commodity, **unfiltered** — every row in the underlying fact counts, measured over `price_date` from `fct_commodity_trading_signals_daily`, and carried as `realised_vol_total` / `realised_vol_days` so it re-divides correctly at any grain. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

> **Ratio metric.** Aggregated as `sum(realised_vol_total) / sum(realised_vol_days)` at whatever grain you group by. Averaging the ratio itself gives a different — and wrong — answer.

```sql series
select metric_time, sum(realised_vol_total) as realised_vol_total, sum(realised_vol_days) as realised_vol_days, sum(realised_vol_total) / nullif(sum(realised_vol_days), 0) as avg_realised_vol
from ${metrics_avg_realised_vol} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=avg_realised_vol yFmt=num0/>

## By commodity id

```sql by_dim
select commodity_id, sum(realised_vol_total) / nullif(sum(realised_vol_days), 0) as avg_realised_vol
from ${metrics_avg_realised_vol} where commodity_id is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=commodity_id y=avg_realised_vol swapXY=true xFmt=num0/>

