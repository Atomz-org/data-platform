---
title: Avg Import Parity Ratio
queries:
  - metrics/avg_import_parity_ratio.sql
---

Landed over benchmark, both in USD per quote unit — 1.15 means landing adds 15%. Group by commodity and market, **unfiltered** — every row in the underlying fact counts, measured over `price_date` from `fct_landed_prices_daily`, and carried as `landed_usd_total` / `benchmark_usd_total_where_landed` so it re-divides correctly at any grain. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

> **Ratio metric.** Aggregated as `sum(landed_usd_total) / sum(benchmark_usd_total_where_landed)` at whatever grain you group by. Averaging the ratio itself gives a different — and wrong — answer.

```sql series
select metric_time, sum(landed_usd_total) as landed_usd_total, sum(benchmark_usd_total_where_landed) as benchmark_usd_total_where_landed, sum(landed_usd_total) / nullif(sum(benchmark_usd_total_where_landed), 0) as avg_import_parity_ratio
from ${metrics_avg_import_parity_ratio} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=avg_import_parity_ratio yFmt=num0/>

## By commodity id

```sql by_dim
select commodity_id, sum(landed_usd_total) / nullif(sum(benchmark_usd_total_where_landed), 0) as avg_import_parity_ratio
from ${metrics_avg_import_parity_ratio} where commodity_id is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=commodity_id y=avg_import_parity_ratio swapXY=true xFmt=num0/>

