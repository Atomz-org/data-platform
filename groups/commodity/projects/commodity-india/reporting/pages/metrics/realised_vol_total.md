---
title: Realised Volatility (component)
queries:
  - metrics/realised_vol_total.sql
---

The `realised_vol_total` metric, **unfiltered** — every row in the underlying fact counts, measured over `price_date` from `fct_commodity_trading_signals_daily`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(realised_vol_total) as realised_vol_total
from ${metrics_realised_vol_total} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=realised_vol_total yFmt=num0/>

## By commodity id

```sql by_dim
select commodity_id, sum(realised_vol_total) as realised_vol_total
from ${metrics_realised_vol_total} where commodity_id is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=commodity_id y=realised_vol_total swapXY=true xFmt=num0/>

