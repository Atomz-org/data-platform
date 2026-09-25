---
title: Avg Rupee Share of the Move
queries:
  - metrics/avg_fx_share_of_move.sql
---

Share of the 20-day landed move attributable to USD/INR rather than the benchmark or duty. High means the commodity call and the currency call have come apart, and timing the commodity will not recover the cost.
, **unfiltered** — every row in the underlying fact counts, measured over `price_date` from `fct_landed_price_attribution_daily`, and carried as `fx_share_total` / `fx_share_days` so it re-divides correctly at any grain. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

> **Ratio metric.** Aggregated as `sum(fx_share_total) / sum(fx_share_days)` at whatever grain you group by. Averaging the ratio itself gives a different — and wrong — answer.

```sql series
select metric_time, sum(fx_share_total) as fx_share_total, sum(fx_share_days) as fx_share_days, sum(fx_share_total) / nullif(sum(fx_share_days), 0) as avg_fx_share_of_move
from ${metrics_avg_fx_share_of_move} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=avg_fx_share_of_move yFmt=num0/>

## By commodity id

```sql by_dim
select commodity_id, sum(fx_share_total) / nullif(sum(fx_share_days), 0) as avg_fx_share_of_move
from ${metrics_avg_fx_share_of_move} where commodity_id is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=commodity_id y=avg_fx_share_of_move swapXY=true xFmt=num0/>

