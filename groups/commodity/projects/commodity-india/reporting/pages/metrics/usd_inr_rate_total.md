---
title: USD/INR Total (component)
queries:
  - metrics/usd_inr_rate_total.sql
---

Building block for avg_usd_inr_rate, **restricted to `quote_currency_code = 'INR'`**, measured over `rate_date` from `fct_fx_rates_daily`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(usd_inr_rate_total) as usd_inr_rate_total
from ${metrics_usd_inr_rate_total} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=usd_inr_rate_total yFmt=num0/>

## By quote currency code

```sql by_dim
select quote_currency_code, sum(usd_inr_rate_total) as usd_inr_rate_total
from ${metrics_usd_inr_rate_total} where quote_currency_code is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=quote_currency_code y=usd_inr_rate_total swapXY=true xFmt=num0/>

