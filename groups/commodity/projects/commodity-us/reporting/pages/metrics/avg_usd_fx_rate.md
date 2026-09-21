---
title: Avg Applied FX Rate
queries:
  - metrics/avg_usd_fx_rate.sql
---

Mean units of this market's currency per US dollar, as applied to landed prices; 1 for a USD market, **unfiltered** — every row in the underlying fact counts, measured over `price_date` from `fct_landed_prices_daily`, and carried as `usd_fx_rate_total` / `landed_price_days` so it re-divides correctly at any grain. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

> **Ratio metric.** Aggregated as `sum(usd_fx_rate_total) / sum(landed_price_days)` at whatever grain you group by. Averaging the ratio itself gives a different — and wrong — answer.

```sql series
select metric_time, sum(usd_fx_rate_total) as usd_fx_rate_total, sum(landed_price_days) as landed_price_days, sum(usd_fx_rate_total) / nullif(sum(landed_price_days), 0) as avg_usd_fx_rate
from ${metrics_avg_usd_fx_rate} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=avg_usd_fx_rate yFmt=num0/>

## By commodity id

```sql by_dim
select commodity_id, sum(usd_fx_rate_total) / nullif(sum(landed_price_days), 0) as avg_usd_fx_rate
from ${metrics_avg_usd_fx_rate} where commodity_id is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=commodity_id y=avg_usd_fx_rate swapXY=true xFmt=num0/>

