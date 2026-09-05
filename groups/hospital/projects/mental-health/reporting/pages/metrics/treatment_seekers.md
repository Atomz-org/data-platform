---
title: Treatment Seekers
queries:
  - metrics/treatment_seekers.sql
---

Distinct survey respondents who sought treatment, **unfiltered** — every row in the underlying fact counts, measured over `surveyed_at` from `fct_survey_responses`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(treatment_seekers) as treatment_seekers
from ${metrics_treatment_seekers} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=treatment_seekers yFmt=num0/>

## By country

```sql by_dim
select country, sum(treatment_seekers) as treatment_seekers
from ${metrics_treatment_seekers} where country is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=country y=treatment_seekers swapXY=true xFmt=num0/>

