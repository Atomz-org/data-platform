---
title: Registry In-patients
queries:
  - metrics/registry_inpatients.sql
---

National psychiatric in-patient count — both sexes, count unit only, suppressed cells excluded by NULL semantics, **restricted to `unit = 'number'
and sex = 'both sexes'
and conformed_icd10_group <> 'all disorders'`**, measured over `year_date` from `fct_registry_annual`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(registry_inpatients) as registry_inpatients
from ${metrics_registry_inpatients} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=registry_inpatients yFmt=num0/>

## By sex

```sql by_dim
select sex, sum(registry_inpatients) as registry_inpatients
from ${metrics_registry_inpatients} where sex is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=sex y=registry_inpatients swapXY=true xFmt=num0/>

