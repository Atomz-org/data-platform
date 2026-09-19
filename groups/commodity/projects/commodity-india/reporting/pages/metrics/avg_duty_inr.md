---
title: Avg Customs Duty (INR)
queries:
  - metrics/avg_duty_inr.sql
---

Mean customs duty per Indian market unit. Group by commodity, **unfiltered** — every row in the underlying fact counts, measured over `price_date` from `fct_india_landed_prices_daily`, and carried as `duty_inr_total` / `landed_price_days` so it re-divides correctly at any grain. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

> **Ratio metric.** Aggregated as `sum(duty_inr_total) / sum(landed_price_days)` at whatever grain you group by. Averaging the ratio itself gives a different — and wrong — answer.

```sql series
select metric_time, sum(duty_inr_total) as duty_inr_total, sum(landed_price_days) as landed_price_days, sum(duty_inr_total) / nullif(sum(landed_price_days), 0) as avg_duty_inr
from ${metrics_avg_duty_inr} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=avg_duty_inr yFmt=num0/>

## By commodity id

```sql by_dim
select commodity_id, sum(duty_inr_total) / nullif(sum(landed_price_days), 0) as avg_duty_inr
from ${metrics_avg_duty_inr} where commodity_id is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=commodity_id y=avg_duty_inr swapXY=true xFmt=num0/>

