---
title: Avg Symptom Severity
queries:
  - metrics/avg_symptom_severity.sql
---

Mean symptom severity (1-10) across episodes, **unfiltered** — every row in the underlying fact counts, measured over `treatment_started_at` from `fct_treatment_episodes`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(avg_symptom_severity) as avg_symptom_severity
from ${metrics_avg_symptom_severity} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=avg_symptom_severity yFmt=num0/>

## By outcome

```sql by_dim
select outcome, sum(avg_symptom_severity) as avg_symptom_severity
from ${metrics_avg_symptom_severity} where outcome is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=outcome y=avg_symptom_severity swapXY=true xFmt=num0/>

