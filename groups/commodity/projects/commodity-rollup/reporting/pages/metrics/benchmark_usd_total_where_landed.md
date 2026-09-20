---
title: Benchmark USD Total, landed days (component)
queries:
  - metrics/benchmark_usd_total_where_landed.sql
---

Building block for avg_import_parity_ratio — the benchmark on exactly the days a landed price exists, **unfiltered** — every row in the underlying fact counts, measured over `price_date` from `fct_landed_prices_daily`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(benchmark_usd_total_where_landed) as benchmark_usd_total_where_landed
from ${metrics_benchmark_usd_total_where_landed} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=benchmark_usd_total_where_landed yFmt=num0/>

## By commodity id

```sql by_dim
select commodity_id, sum(benchmark_usd_total_where_landed) as benchmark_usd_total_where_landed
from ${metrics_benchmark_usd_total_where_landed} where commodity_id is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=commodity_id y=benchmark_usd_total_where_landed swapXY=true xFmt=num0/>

