---
title: Treatment-Seeking Rate
queries:
  - metrics/treatment_seeking_rate.sql
---

Share of distinct survey respondents who sought treatment. Population context — never a clinical outcome, **unfiltered** — every row in the underlying fact counts, measured over `surveyed_at` from `fct_survey_responses`, and carried as `treatment_seekers` / `survey_responses` so it re-divides correctly at any grain. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

> **Ratio metric.** Aggregated as `sum(treatment_seekers) / sum(survey_responses)` at whatever grain you group by. Averaging the ratio itself gives a different — and wrong — answer.

```sql series
select metric_time, sum(treatment_seekers) as treatment_seekers, sum(survey_responses) as survey_responses, sum(treatment_seekers) / nullif(sum(survey_responses), 0) as treatment_seeking_rate
from ${metrics_treatment_seeking_rate} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=treatment_seeking_rate yFmt=num0/>

## By country

```sql by_dim
select country, sum(treatment_seekers) / nullif(sum(survey_responses), 0) as treatment_seeking_rate
from ${metrics_treatment_seeking_rate} where country is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=country y=treatment_seeking_rate swapXY=true xFmt=num0/>

