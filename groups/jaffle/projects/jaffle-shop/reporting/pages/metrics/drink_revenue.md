---
title: Drink Revenue
queries:
  - metrics/drink_revenue.sql
---

The revenue from drinks in each order, **unfiltered** — every row in the underlying fact counts, measured over `ordered_at` from `order_items`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(drink_revenue) as drink_revenue
from ${metrics_drink_revenue} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=drink_revenue yFmt=usd0/>

## By is food item

```sql by_dim
select is_food_item, sum(drink_revenue) as drink_revenue
from ${metrics_drink_revenue} where is_food_item is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=is_food_item y=drink_revenue swapXY=true xFmt=usd0/>

