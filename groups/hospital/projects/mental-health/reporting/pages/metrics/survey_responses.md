---
title: Survey Responses
queries:
  - metrics/survey_responses.sql
---

Distinct population survey responses (upstream duplication removed), **unfiltered** — every row in the underlying fact counts, measured over `surveyed_at` from `fct_survey_responses`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(survey_responses) as survey_responses
from ${metrics_survey_responses} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=survey_responses yFmt=num0/>

## By country

```sql by_dim
select country, sum(survey_responses) as survey_responses
from ${metrics_survey_responses} where country is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=country y=survey_responses swapXY=true xFmt=num0/>

