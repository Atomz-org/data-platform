---
title: Revenue Growth % M/M
queries:
  - metrics/revenue_growth_mom.sql
---

Percentage growth of revenue compared to 1 month ago. Excluded tax, **unfiltered** — every row in the underlying fact counts, measured over `ordered_at` from `order_items`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(revenue_growth_mom) as revenue_growth_mom
from ${metrics_revenue_growth_mom} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=revenue_growth_mom yFmt=usd0/>

## By is food item

```sql by_dim
select is_food_item, sum(revenue_growth_mom) as revenue_growth_mom
from ${metrics_revenue_growth_mom} where is_food_item is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=is_food_item y=revenue_growth_mom swapXY=true xFmt=usd0/>

