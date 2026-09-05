---
title: Adherence Rate
queries:
  - metrics/adherence_rate.sql
---

Mean adherence to treatment, in percent, across episodes, **unfiltered** — every row in the underlying fact counts, measured over `treatment_started_at` from `fct_treatment_episodes`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(adherence_rate) as adherence_rate
from ${metrics_adherence_rate} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=adherence_rate yFmt=num0/>

## By outcome

```sql by_dim
select outcome, sum(adherence_rate) as adherence_rate
from ${metrics_adherence_rate} where outcome is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=outcome y=adherence_rate swapXY=true xFmt=num0/>

