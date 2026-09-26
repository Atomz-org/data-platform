---
title: Volume (flagship-lot equivalents) — per Commodity
queries:
  - metrics/mcx_commodity_volume_flagship_lots.sql
---

Turnover restated in lots of the flagship contract, so GOLD, GOLDM and GOLDPETAL add up. Group by mcx_commodity — a gold lot is not a crude lot, **unfiltered** — every row in the underlying fact counts, measured over `trade_date` from `fct_mcx_commodity_rollup_daily`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(mcx_commodity_volume_flagship_lots) as mcx_commodity_volume_flagship_lots
from ${metrics_mcx_commodity_volume_flagship_lots} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=mcx_commodity_volume_flagship_lots yFmt=num0/>

## By mcx commodity

```sql by_dim
select mcx_commodity, sum(mcx_commodity_volume_flagship_lots) as mcx_commodity_volume_flagship_lots
from ${metrics_mcx_commodity_volume_flagship_lots} where mcx_commodity is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=mcx_commodity y=mcx_commodity_volume_flagship_lots swapXY=true xFmt=num0/>

