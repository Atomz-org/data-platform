---
title: Contracts Traded
queries:
  - metrics/contracts_traded.sql
---

Front-month futures volume from live feeds. Group by commodity, **restricted to `price_basis = 'futures'`**, measured over `price_date` from `fct_commodity_prices_daily`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(contracts_traded) as contracts_traded
from ${metrics_contracts_traded} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=contracts_traded yFmt=num0/>

## By commodity id

```sql by_dim
select commodity_id, sum(contracts_traded) as contracts_traded
from ${metrics_contracts_traded} where commodity_id is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=commodity_id y=contracts_traded swapXY=true xFmt=num0/>

