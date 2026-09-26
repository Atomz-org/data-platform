---
title: MCX Futures Volume (lots)
queries:
  - metrics/mcx_volume_lots.sql
---

Lots traded across every expiry. Additive within a code; a GOLD lot is not a GOLDPETAL lot, so compare across codes with turnover instead, **unfiltered** — every row in the underlying fact counts, measured over `trade_date` from `fct_mcx_commodity_daily`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(mcx_volume_lots) as mcx_volume_lots
from ${metrics_mcx_volume_lots} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=mcx_volume_lots yFmt=num0/>

## By contract code

```sql by_dim
select contract_code, sum(mcx_volume_lots) as mcx_volume_lots
from ${metrics_mcx_volume_lots} where contract_code is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=contract_code y=mcx_volume_lots swapXY=true xFmt=num0/>

