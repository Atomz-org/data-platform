---
title: Avg MCX Premium to Landed Parity
queries:
  - metrics/avg_mcx_premium_to_landed.sql
---

MCX settlement over the landed import-parity price of the same quote basis, minus one. Only codes the family prices. Group by contract_code, **unfiltered** — every row in the underlying fact counts, measured over `trade_date` from `fct_mcx_commodity_daily`, and carried as `mcx_premium_total` / `mcx_premium_days` so it re-divides correctly at any grain. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

> **Ratio metric.** Aggregated as `sum(mcx_premium_total) / sum(mcx_premium_days)` at whatever grain you group by. Averaging the ratio itself gives a different — and wrong — answer.

```sql series
select metric_time, sum(mcx_premium_total) as mcx_premium_total, sum(mcx_premium_days) as mcx_premium_days, sum(mcx_premium_total) / nullif(sum(mcx_premium_days), 0) as avg_mcx_premium_to_landed
from ${metrics_avg_mcx_premium_to_landed} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=avg_mcx_premium_to_landed yFmt=pct2/>

## By contract code

```sql by_dim
select contract_code, sum(mcx_premium_total) / nullif(sum(mcx_premium_days), 0) as avg_mcx_premium_to_landed
from ${metrics_avg_mcx_premium_to_landed} where contract_code is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=contract_code y=avg_mcx_premium_to_landed swapXY=true xFmt=pct2/>

