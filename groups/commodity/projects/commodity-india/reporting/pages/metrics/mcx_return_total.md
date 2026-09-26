---
title: MCX Summed Daily Return (component)
queries:
  - metrics/mcx_return_total.sql
---

The `mcx_return_total` metric, **unfiltered** — every row in the underlying fact counts, measured over `trade_date` from `fct_mcx_commodity_daily`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(mcx_return_total) as mcx_return_total
from ${metrics_mcx_return_total} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=mcx_return_total yFmt=num3/>

## By contract code

```sql by_dim
select contract_code, sum(mcx_return_total) as mcx_return_total
from ${metrics_mcx_return_total} where contract_code is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=contract_code y=mcx_return_total swapXY=true xFmt=num3/>

