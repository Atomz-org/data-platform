---
title: Applied FX Rate Total (component)
queries:
  - metrics/usd_fx_rate_total.sql
---

Building block for avg_usd_fx_rate — the rate each landed price actually used, **unfiltered** — every row in the underlying fact counts, measured over `price_date` from `fct_landed_prices_daily`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(usd_fx_rate_total) as usd_fx_rate_total
from ${metrics_usd_fx_rate_total} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=usd_fx_rate_total yFmt=usd/>

## By commodity id

```sql by_dim
select commodity_id, sum(usd_fx_rate_total) as usd_fx_rate_total
from ${metrics_usd_fx_rate_total} where commodity_id is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=commodity_id y=usd_fx_rate_total swapXY=true xFmt=usd/>

