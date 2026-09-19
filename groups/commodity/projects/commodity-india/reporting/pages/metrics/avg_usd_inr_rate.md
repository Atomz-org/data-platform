---
title: Avg USD/INR
queries:
  - metrics/avg_usd_inr_rate.sql
---

Mean rupees per US dollar, the rate every landed price uses, **restricted to `quote_currency_code = 'INR'`**, measured over `rate_date` from `fct_fx_rates_daily`, and carried as `usd_inr_rate_total` / `usd_inr_rate_days` so it re-divides correctly at any grain. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

> **Ratio metric.** Aggregated as `sum(usd_inr_rate_total) / sum(usd_inr_rate_days)` at whatever grain you group by. Averaging the ratio itself gives a different — and wrong — answer.

```sql series
select metric_time, sum(usd_inr_rate_total) as usd_inr_rate_total, sum(usd_inr_rate_days) as usd_inr_rate_days, sum(usd_inr_rate_total) / nullif(sum(usd_inr_rate_days), 0) as avg_usd_inr_rate
from ${metrics_avg_usd_inr_rate} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=avg_usd_inr_rate yFmt=num0/>

## By quote currency code

```sql by_dim
select quote_currency_code, sum(usd_inr_rate_total) / nullif(sum(usd_inr_rate_days), 0) as avg_usd_inr_rate
from ${metrics_avg_usd_inr_rate} where quote_currency_code is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=quote_currency_code y=avg_usd_inr_rate swapXY=true xFmt=num0/>

