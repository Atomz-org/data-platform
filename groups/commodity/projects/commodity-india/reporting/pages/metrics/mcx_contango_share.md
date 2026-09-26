---
title: MCX Share of Sessions in Contango
queries:
  - metrics/mcx_contango_share.sql
---

Contango sessions over all sessions. Group by contract_code, **unfiltered** — every row in the underlying fact counts, measured over `trade_date` from `fct_mcx_commodity_daily`, and carried as `mcx_contango_days` / `mcx_session_days` so it re-divides correctly at any grain. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

> **Ratio metric.** Aggregated as `sum(mcx_contango_days) / sum(mcx_session_days)` at whatever grain you group by. Averaging the ratio itself gives a different — and wrong — answer.

```sql series
select metric_time, sum(mcx_contango_days) as mcx_contango_days, sum(mcx_session_days) as mcx_session_days, sum(mcx_contango_days) / nullif(sum(mcx_session_days), 0) as mcx_contango_share
from ${metrics_mcx_contango_share} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=mcx_contango_share yFmt=pct1/>

## By contract code

```sql by_dim
select contract_code, sum(mcx_contango_days) / nullif(sum(mcx_session_days), 0) as mcx_contango_share
from ${metrics_mcx_contango_share} where contract_code is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=contract_code y=mcx_contango_share swapXY=true xFmt=pct1/>

