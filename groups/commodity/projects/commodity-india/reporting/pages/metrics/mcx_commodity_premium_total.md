---
title: Landed-Parity Premium (component) — per Commodity
queries:
  - metrics/mcx_commodity_premium_total.sql
---

The `mcx_commodity_premium_total` metric, **unfiltered** — every row in the underlying fact counts, measured over `trade_date` from `fct_mcx_commodity_rollup_daily`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(mcx_commodity_premium_total) as mcx_commodity_premium_total
from ${metrics_mcx_commodity_premium_total} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=mcx_commodity_premium_total yFmt=num3/>

## By mcx commodity

```sql by_dim
select mcx_commodity, sum(mcx_commodity_premium_total) as mcx_commodity_premium_total
from ${metrics_mcx_commodity_premium_total} where mcx_commodity is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=mcx_commodity y=mcx_commodity_premium_total swapXY=true xFmt=num3/>

