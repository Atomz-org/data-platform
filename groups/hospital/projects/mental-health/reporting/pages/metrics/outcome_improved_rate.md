---
title: Improved Outcome Rate
queries:
  - metrics/outcome_improved_rate.sql
---

Share of episodes whose recorded outcome is 'improved', **unfiltered** — every row in the underlying fact counts, measured over `treatment_started_at` from `fct_treatment_episodes`, and carried as `improved_episodes` / `treatment_episodes` so it re-divides correctly at any grain. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

> **Ratio metric.** Aggregated as `sum(improved_episodes) / sum(treatment_episodes)` at whatever grain you group by. Averaging the ratio itself gives a different — and wrong — answer.

```sql series
select metric_time, sum(improved_episodes) as improved_episodes, sum(treatment_episodes) as treatment_episodes, sum(improved_episodes) / nullif(sum(treatment_episodes), 0) as outcome_improved_rate
from ${metrics_outcome_improved_rate} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=outcome_improved_rate yFmt=num0/>

## By outcome

```sql by_dim
select outcome, sum(improved_episodes) / nullif(sum(treatment_episodes), 0) as outcome_improved_rate
from ${metrics_outcome_improved_rate} where outcome is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=outcome y=outcome_improved_rate swapXY=true xFmt=num0/>

