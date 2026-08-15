---
title: Median Revenue
queries:
  - metrics/median_revenue.sql
---

The median revenue for each order item. Excludes tax, **unfiltered** — every row in the underlying fact counts, measured over `ordered_at` from `order_items`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(median_revenue) as median_revenue
from ${metrics_median_revenue} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=median_revenue yFmt=usd0/>

## By is food item

```sql by_dim
select is_food_item, sum(median_revenue) as median_revenue
from ${metrics_median_revenue} where is_food_item is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=is_food_item y=median_revenue swapXY=true xFmt=usd0/>

