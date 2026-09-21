---
title: Median Revenue
queries:
  - metrics/median_revenue.sql
---

The median revenue for each order item. Excludes tax, **unfiltered** — every row in the underlying fact counts, measured over `ordered_at` from `order_items`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

> **Not additive.** A `median` cannot be rebuilt from grouped rows, so the series is shown exactly as the metric computed it, per `ordered_at`.

```sql series
select metric_time, median_revenue
from ${metrics_median_revenue} order by 1
```

<LineChart data={series} x=metric_time y=median_revenue yFmt=usd0/>

