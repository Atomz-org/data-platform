---
title: Range Position (component)
queries:
  - metrics/range_position_total.sql
---

Sum of daily range positions. A component of avg_range_position, not a figure to read, **unfiltered** — every row in the underlying fact counts, measured over `price_date` from `fct_commodity_trading_signals_daily`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(range_position_total) as range_position_total
from ${metrics_range_position_total} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=range_position_total yFmt=num0/>

## By commodity id

```sql by_dim
select commodity_id, sum(range_position_total) as range_position_total
from ${metrics_range_position_total} where commodity_id is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=commodity_id y=range_position_total swapXY=true xFmt=num0/>

