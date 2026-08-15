---
title: New Customers
queries:
  - metrics/new_customer_orders.sql
---

New customer's first order count, **restricted to `customer_order_number = 1`**, measured over `ordered_at` from `orders`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(new_customer_orders) as new_customer_orders
from ${metrics_new_customer_orders} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=new_customer_orders yFmt=num0/>

## By order total dim

```sql by_dim
select order_total_dim, sum(new_customer_orders) as new_customer_orders
from ${metrics_new_customer_orders} where order_total_dim is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=order_total_dim y=new_customer_orders swapXY=true xFmt=num0/>

