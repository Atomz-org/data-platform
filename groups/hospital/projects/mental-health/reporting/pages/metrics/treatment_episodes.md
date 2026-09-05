---
title: Treatment Episodes
queries:
  - metrics/treatment_episodes.sql
---

Count of treatment episodes. The single definition, **unfiltered** — every row in the underlying fact counts, measured over `treatment_started_at` from `fct_treatment_episodes`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(treatment_episodes) as treatment_episodes
from ${metrics_treatment_episodes} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=treatment_episodes yFmt=num0/>

## By outcome

```sql by_dim
select outcome, sum(treatment_episodes) as treatment_episodes
from ${metrics_treatment_episodes} where outcome is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=outcome y=treatment_episodes swapXY=true xFmt=num0/>

