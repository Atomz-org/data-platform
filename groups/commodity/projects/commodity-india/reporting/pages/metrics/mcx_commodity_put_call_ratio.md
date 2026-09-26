---
title: Put/Call Ratio (notional OI) — per Commodity
queries:
  - metrics/mcx_commodity_put_call_ratio.sql
---

Put open interest over call, each weighted by its underlying's notional per lot so every code of the commodity counts at its size. Above ~1.3 put-heavy, below ~0.7 call-heavy, **unfiltered** — every row in the underlying fact counts, measured over `trade_date` from `fct_mcx_commodity_rollup_daily`, and carried as `mcx_commodity_put_oi_notional_inr` / `mcx_commodity_call_oi_notional_inr` so it re-divides correctly at any grain. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

> **Ratio metric.** Aggregated as `sum(mcx_commodity_put_oi_notional_inr) / sum(mcx_commodity_call_oi_notional_inr)` at whatever grain you group by. Averaging the ratio itself gives a different — and wrong — answer.

```sql series
select metric_time, sum(mcx_commodity_put_oi_notional_inr) as mcx_commodity_put_oi_notional_inr, sum(mcx_commodity_call_oi_notional_inr) as mcx_commodity_call_oi_notional_inr, sum(mcx_commodity_put_oi_notional_inr) / nullif(sum(mcx_commodity_call_oi_notional_inr), 0) as mcx_commodity_put_call_ratio
from ${metrics_mcx_commodity_put_call_ratio} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=mcx_commodity_put_call_ratio yFmt=num2/>

## By mcx commodity

```sql by_dim
select mcx_commodity, sum(mcx_commodity_put_oi_notional_inr) / nullif(sum(mcx_commodity_call_oi_notional_inr), 0) as mcx_commodity_put_call_ratio
from ${metrics_mcx_commodity_put_call_ratio} where mcx_commodity is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=mcx_commodity y=mcx_commodity_put_call_ratio swapXY=true xFmt=num2/>

