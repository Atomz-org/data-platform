---
title: MCX Roll Yield (component)
queries:
  - metrics/mcx_roll_yield_total.sql
---

The `mcx_roll_yield_total` metric, **unfiltered** — every row in the underlying fact counts, measured over `trade_date` from `fct_mcx_commodity_daily`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(mcx_roll_yield_total) as mcx_roll_yield_total
from ${metrics_mcx_roll_yield_total} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=mcx_roll_yield_total yFmt=num2/>

## By contract code

```sql by_dim
select contract_code, sum(mcx_roll_yield_total) as mcx_roll_yield_total
from ${metrics_mcx_roll_yield_total} where contract_code is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=contract_code y=mcx_roll_yield_total swapXY=true xFmt=num2/>

