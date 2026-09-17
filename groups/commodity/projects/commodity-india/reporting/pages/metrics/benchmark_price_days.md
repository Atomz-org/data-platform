---
title: Priced Days
queries:
  - metrics/benchmark_price_days.sql
---

Days with a benchmark price. Group by commodity to spot feed gaps, **unfiltered** — every row in the underlying fact counts, measured over `price_date` from `fct_commodity_prices_daily`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(benchmark_price_days) as benchmark_price_days
from ${metrics_benchmark_price_days} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=benchmark_price_days yFmt=num0/>

## By commodity id

```sql by_dim
select commodity_id, sum(benchmark_price_days) as benchmark_price_days
from ${metrics_benchmark_price_days} where commodity_id is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=commodity_id y=benchmark_price_days swapXY=true xFmt=num0/>

