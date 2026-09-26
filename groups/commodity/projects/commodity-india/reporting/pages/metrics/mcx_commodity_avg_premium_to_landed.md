---
title: Avg MCX Premium to Landed Parity — per Commodity
queries:
  - metrics/mcx_commodity_avg_premium_to_landed.sql
---

MCX settlement over benchmark × USD/INR × (1 + duty) for the same quote basis, minus one. Only commodities the family prices, **unfiltered** — every row in the underlying fact counts, measured over `trade_date` from `fct_mcx_commodity_rollup_daily`, and carried as `mcx_commodity_premium_total` / `mcx_commodity_premium_days` so it re-divides correctly at any grain. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

> **Ratio metric.** Aggregated as `sum(mcx_commodity_premium_total) / sum(mcx_commodity_premium_days)` at whatever grain you group by. Averaging the ratio itself gives a different — and wrong — answer.

```sql series
select metric_time, sum(mcx_commodity_premium_total) as mcx_commodity_premium_total, sum(mcx_commodity_premium_days) as mcx_commodity_premium_days, sum(mcx_commodity_premium_total) / nullif(sum(mcx_commodity_premium_days), 0) as mcx_commodity_avg_premium_to_landed
from ${metrics_mcx_commodity_avg_premium_to_landed} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=mcx_commodity_avg_premium_to_landed yFmt=pct2/>

## By mcx commodity

```sql by_dim
select mcx_commodity, sum(mcx_commodity_premium_total) / nullif(sum(mcx_commodity_premium_days), 0) as mcx_commodity_avg_premium_to_landed
from ${metrics_mcx_commodity_avg_premium_to_landed} where mcx_commodity is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=mcx_commodity y=mcx_commodity_avg_premium_to_landed swapXY=true xFmt=pct2/>

