---
title: Mini-Contract Turnover (component) — per Commodity
queries:
  - metrics/mcx_commodity_mini_turnover_inr.sql
---

The `mcx_commodity_mini_turnover_inr` metric, **unfiltered** — every row in the underlying fact counts, measured over `trade_date` from `fct_mcx_commodity_rollup_daily`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(mcx_commodity_mini_turnover_inr) as mcx_commodity_mini_turnover_inr
from ${metrics_mcx_commodity_mini_turnover_inr} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=mcx_commodity_mini_turnover_inr yFmt=inr/>

## By mcx commodity

```sql by_dim
select mcx_commodity, sum(mcx_commodity_mini_turnover_inr) as mcx_commodity_mini_turnover_inr
from ${metrics_mcx_commodity_mini_turnover_inr} where mcx_commodity is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=mcx_commodity y=mcx_commodity_mini_turnover_inr swapXY=true xFmt=inr/>

