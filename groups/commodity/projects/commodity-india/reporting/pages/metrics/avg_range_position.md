---
title: Avg Position in 52-Week Range
queries:
  - metrics/avg_range_position.sql
---

0 at the 52-week low, 1 at the high. Group by commodity — averaging this across commodities is a number about the basket, not about anything tradable.
, **unfiltered** — every row in the underlying fact counts, measured over `price_date` from `fct_commodity_trading_signals_daily`, and carried as `range_position_total` / `range_position_days` so it re-divides correctly at any grain. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

> **Ratio metric.** Aggregated as `sum(range_position_total) / sum(range_position_days)` at whatever grain you group by. Averaging the ratio itself gives a different — and wrong — answer.

```sql series
select metric_time, sum(range_position_total) as range_position_total, sum(range_position_days) as range_position_days, sum(range_position_total) / nullif(sum(range_position_days), 0) as avg_range_position
from ${metrics_avg_range_position} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=avg_range_position yFmt=num0/>

## By commodity id

```sql by_dim
select commodity_id, sum(range_position_total) / nullif(sum(range_position_days), 0) as avg_range_position
from ${metrics_avg_range_position} where commodity_id is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=commodity_id y=avg_range_position swapXY=true xFmt=num0/>

