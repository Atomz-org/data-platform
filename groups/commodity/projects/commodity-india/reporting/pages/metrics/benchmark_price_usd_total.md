---
title: Benchmark Price Total (component)
queries:
  - metrics/benchmark_price_usd_total.sql
---

Building block for avg_benchmark_price_usd. A sum of prices means nothing on its own, **unfiltered** — every row in the underlying fact counts, measured over `price_date` from `fct_commodity_prices_daily`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(benchmark_price_usd_total) as benchmark_price_usd_total
from ${metrics_benchmark_price_usd_total} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=benchmark_price_usd_total yFmt=usd/>

## By commodity id

```sql by_dim
select commodity_id, sum(benchmark_price_usd_total) as benchmark_price_usd_total
from ${metrics_benchmark_price_usd_total} where commodity_id is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=commodity_id y=benchmark_price_usd_total swapXY=true xFmt=usd/>

