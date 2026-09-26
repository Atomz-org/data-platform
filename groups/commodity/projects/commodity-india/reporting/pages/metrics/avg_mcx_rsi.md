---
title: Avg MCX RSI(14)
queries:
  - metrics/avg_mcx_rsi.sql
---

Wilder RSI on the roll-free continuous series. Group by contract_code, **unfiltered** — every row in the underlying fact counts, measured over `trade_date` from `fct_mcx_commodity_daily`, and carried as `mcx_rsi_total` / `mcx_rsi_days` so it re-divides correctly at any grain. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

> **Ratio metric.** Aggregated as `sum(mcx_rsi_total) / sum(mcx_rsi_days)` at whatever grain you group by. Averaging the ratio itself gives a different — and wrong — answer.

```sql series
select metric_time, sum(mcx_rsi_total) as mcx_rsi_total, sum(mcx_rsi_days) as mcx_rsi_days, sum(mcx_rsi_total) / nullif(sum(mcx_rsi_days), 0) as avg_mcx_rsi
from ${metrics_avg_mcx_rsi} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=avg_mcx_rsi yFmt=num1/>

## By contract code

```sql by_dim
select contract_code, sum(mcx_rsi_total) / nullif(sum(mcx_rsi_days), 0) as avg_mcx_rsi
from ${metrics_avg_mcx_rsi} where contract_code is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=contract_code y=avg_mcx_rsi swapXY=true xFmt=num1/>

