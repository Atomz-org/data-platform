---
title: LTV Pre-tax
queries:
  - metrics/lifetime_spend_pretax.sql
---

Customer's lifetime spend before tax, **unfiltered** — every row in the underlying fact counts, measured over `first_ordered_at` from `customers`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(lifetime_spend_pretax) as lifetime_spend_pretax
from ${metrics_lifetime_spend_pretax} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=lifetime_spend_pretax yFmt=num0/>

## By customer name

```sql by_dim
select customer_name, sum(lifetime_spend_pretax) as lifetime_spend_pretax
from ${metrics_lifetime_spend_pretax} where customer_name is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=customer_name y=lifetime_spend_pretax swapXY=true xFmt=num0/>

