---
title: Order Gross Profit
queries:
  - metrics/order_gross_profit.sql
---

Gross profit from each order, **unfiltered** — every row in the underlying fact counts, measured over `ordered_at` from `order_items`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(order_gross_profit) as order_gross_profit
from ${metrics_order_gross_profit} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=order_gross_profit yFmt=num0/>

## By is food item

```sql by_dim
select is_food_item, sum(order_gross_profit) as order_gross_profit
from ${metrics_order_gross_profit} where is_food_item is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=is_food_item y=order_gross_profit swapXY=true xFmt=num0/>

