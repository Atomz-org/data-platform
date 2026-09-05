---
title: Avg Treatment Duration (weeks)
queries:
  - metrics/avg_treatment_duration.sql
---

Mean episode duration in weeks, **unfiltered** — every row in the underlying fact counts, measured over `treatment_started_at` from `fct_treatment_episodes`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(avg_treatment_duration) as avg_treatment_duration
from ${metrics_avg_treatment_duration} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=avg_treatment_duration yFmt=num0/>

## By outcome

```sql by_dim
select outcome, sum(avg_treatment_duration) as avg_treatment_duration
from ${metrics_avg_treatment_duration} where outcome is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=outcome y=avg_treatment_duration swapXY=true xFmt=num0/>

