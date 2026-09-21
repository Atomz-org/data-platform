---
title: Food Revenue %
queries:
  - metrics/food_revenue_pct.sql
---

The % of order revenue from food, **unfiltered** — every row in the underlying fact counts, measured over `ordered_at` from `order_items`, and carried as `food_revenue` / `revenue` so it re-divides correctly at any grain. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

> **Ratio metric.** Aggregated as `sum(food_revenue) / sum(revenue)` at whatever grain you group by. Averaging the ratio itself gives a different — and wrong — answer.

```sql series
select metric_time, sum(food_revenue) as food_revenue, sum(revenue) as revenue, sum(food_revenue) / nullif(sum(revenue), 0) as food_revenue_pct
from ${metrics_food_revenue_pct} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=food_revenue_pct yFmt=usd0/>

## By is food item

```sql by_dim
select is_food_item, sum(food_revenue) / nullif(sum(revenue), 0) as food_revenue_pct
from ${metrics_food_revenue_pct} where is_food_item is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=is_food_item y=food_revenue_pct swapXY=true xFmt=usd0/>

