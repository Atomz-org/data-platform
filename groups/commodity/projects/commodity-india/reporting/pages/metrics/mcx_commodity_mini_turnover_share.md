---
title: Mini-Contract Share of Turnover — per Commodity
queries:
  - metrics/mcx_commodity_mini_turnover_share.sql
---

Turnover in the non-flagship codes (GOLDM, SILVERMIC, CRUDEOILM, ...) over all turnover — how retail the commodity's book is, **unfiltered** — every row in the underlying fact counts, measured over `trade_date` from `fct_mcx_commodity_rollup_daily`, and carried as `mcx_commodity_mini_turnover_inr` / `mcx_commodity_turnover_inr` so it re-divides correctly at any grain. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

> **Ratio metric.** Aggregated as `sum(mcx_commodity_mini_turnover_inr) / sum(mcx_commodity_turnover_inr)` at whatever grain you group by. Averaging the ratio itself gives a different — and wrong — answer.

```sql series
select metric_time, sum(mcx_commodity_mini_turnover_inr) as mcx_commodity_mini_turnover_inr, sum(mcx_commodity_turnover_inr) as mcx_commodity_turnover_inr, sum(mcx_commodity_mini_turnover_inr) / nullif(sum(mcx_commodity_turnover_inr), 0) as mcx_commodity_mini_turnover_share
from ${metrics_mcx_commodity_mini_turnover_share} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=mcx_commodity_mini_turnover_share yFmt=pct1/>

## By mcx commodity

```sql by_dim
select mcx_commodity, sum(mcx_commodity_mini_turnover_inr) / nullif(sum(mcx_commodity_turnover_inr), 0) as mcx_commodity_mini_turnover_share
from ${metrics_mcx_commodity_mini_turnover_share} where mcx_commodity is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=mcx_commodity y=mcx_commodity_mini_turnover_share swapXY=true xFmt=pct1/>

