---
title: MCX Days With an RSI Reading
queries:
  - metrics/mcx_rsi_days.sql
---

The `mcx_rsi_days` metric, **unfiltered** — every row in the underlying fact counts, measured over `trade_date` from `fct_mcx_commodity_daily`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(mcx_rsi_days) as mcx_rsi_days
from ${metrics_mcx_rsi_days} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=mcx_rsi_days yFmt=num0/>

## By contract code

```sql by_dim
select contract_code, sum(mcx_rsi_days) as mcx_rsi_days
from ${metrics_mcx_rsi_days} where contract_code is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=contract_code y=mcx_rsi_days swapXY=true xFmt=num0/>

