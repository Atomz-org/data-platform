---
title: MCX Futures Turnover (₹)
queries:
  - metrics/mcx_turnover_inr.sql
---

Traded value across every expiry, in rupees. Additive across codes and days, **unfiltered** — every row in the underlying fact counts, measured over `trade_date` from `fct_mcx_commodity_daily`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(mcx_turnover_inr) as mcx_turnover_inr
from ${metrics_mcx_turnover_inr} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=mcx_turnover_inr yFmt=inr/>

## By contract code

```sql by_dim
select contract_code, sum(mcx_turnover_inr) as mcx_turnover_inr
from ${metrics_mcx_turnover_inr} where contract_code is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=contract_code y=mcx_turnover_inr swapXY=true xFmt=inr/>

