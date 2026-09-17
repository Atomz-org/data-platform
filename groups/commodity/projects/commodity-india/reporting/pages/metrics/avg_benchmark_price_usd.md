---
title: Avg Benchmark Price (USD)
queries:
  - metrics/avg_benchmark_price_usd.sql
---

Mean daily settlement price, USD per quote unit. Group by commodity, **unfiltered** — every row in the underlying fact counts, measured over `price_date` from `fct_commodity_prices_daily`, and carried as `benchmark_price_usd_total` / `benchmark_price_days` so it re-divides correctly at any grain. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

> **Ratio metric.** Aggregated as `sum(benchmark_price_usd_total) / sum(benchmark_price_days)` at whatever grain you group by. Averaging the ratio itself gives a different — and wrong — answer.

```sql series
select metric_time, sum(benchmark_price_usd_total) as benchmark_price_usd_total, sum(benchmark_price_days) as benchmark_price_days, sum(benchmark_price_usd_total) / nullif(sum(benchmark_price_days), 0) as avg_benchmark_price_usd
from ${metrics_avg_benchmark_price_usd} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=avg_benchmark_price_usd yFmt=num0/>

## By commodity id

```sql by_dim
select commodity_id, sum(benchmark_price_usd_total) / nullif(sum(benchmark_price_days), 0) as avg_benchmark_price_usd
from ${metrics_avg_benchmark_price_usd} where commodity_id is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=commodity_id y=avg_benchmark_price_usd swapXY=true xFmt=num0/>

