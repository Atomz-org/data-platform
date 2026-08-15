---
title: Revenue
queries:
  - metrics/revenue.sql
---

Sum of the product revenue for each order item. Excludes tax, **unfiltered** — every row in the underlying fact counts, measured over `ordered_at` from `order_items`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(revenue) as revenue
from ${metrics_revenue} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=revenue yFmt=usd0/>

## By is food item

```sql by_dim
select is_food_item, sum(revenue) as revenue
from ${metrics_revenue} where is_food_item is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=is_food_item y=revenue swapXY=true xFmt=usd0/>

