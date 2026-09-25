---
title: Signal Days
queries:
  - metrics/signal_days.sql
---

Days with a signal reading. The denominator every mean below divides by, **unfiltered** — every row in the underlying fact counts, measured over `price_date` from `fct_commodity_trading_signals_daily`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(signal_days) as signal_days
from ${metrics_signal_days} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=signal_days yFmt=num0/>

## By commodity id

```sql by_dim
select commodity_id, sum(signal_days) as signal_days
from ${metrics_signal_days} where commodity_id is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=commodity_id y=signal_days swapXY=true xFmt=num0/>

