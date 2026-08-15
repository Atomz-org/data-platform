# dbt-snowflake — Snowflake's function surface, portably

Snowflake functions as dbt macros that compile to whatever the *target* adapter
understands. One set of models runs on DuckDB in development and Snowflake in
production, without a per-database rewrite of anything.

```sql
select {{ sf_iff("status = 'paid'", 'amount', '0') }} as paid_amount
```

| target | compiles to |
| --- | --- |
| DuckDB, Postgres, Redshift | `case when status = 'paid' then amount else 0 end` |
| Snowflake | `iff(status = 'paid', amount, 0)` |
| ClickHouse | `if(status = 'paid', amount, 0)` |

Reached through `macro-paths` in every scaffolded project, so there is nothing to
install. `pf dialect <path>` lists what a tree needs.

## What this is for

Adopting SQL written elsewhere. The alternative — rewriting it for DuckDB —
produces two copies of a project that have to be kept in step and immediately
are not. Wrapping a call site once keeps a single portable source.

## The contract

**The macros reproduce the *source* dialect's semantics, not the local
warehouse's.** That is the whole point, and it is load-bearing in three places:

- `sf_least(['a', 'b'])` returns NULL if either is NULL, as Snowflake does.
  DuckDB, Postgres and BigQuery would skip the NULL and return the other value.
  Use `sf_least_ignore_nulls` when that is what you meant.
- `sf_div0(a, b)` returns **0** on a zero divisor. A hand-written
  `a / nullif(b, 0)` returns NULL — on exactly the rows anyone added the guard
  for.
- `sf_datediff(part, start, end)` takes the part **first**, as Snowflake does.
  dbt-core's own `datediff` takes it last, so passing Snowflake's arguments
  straight through gives a sign-flipped answer in the wrong unit.

Each of those is asserted against a real dbt run in
`platform/tests/test_toolkit_macros.py`, with the value that differs from
DuckDB's native answer marked as such.

## What is deliberately absent

Anything whose meaning depends on which dialect wrote it. `date_trunc` is
`(part, date)` in Snowflake and `(date, part)` in BigQuery; both parse, and one
returns wrong dates silently. Those are listed in `AMBIGUOUS` in
`pf/onboard/dialect.py` and reported by `pf dialect` for a human to resolve. They
are never translated automatically, because a wrong argument order compiles,
runs, and produces numbers no review catches.

## Layout

```
macros/
  conditional.sql   iff, nvl, nvl2, ifnull, zeroifnull, nullifzero, least, greatest
  numeric.sql       div0, div0null, safe_divide, to_number, try_to_number
  datetime.sql      dateadd, datediff, date_trunc, last_day, dayofweek, getdate
  string.sql        charindex, split_part, listagg, regexp_substr, regexp_like, to_varchar
```

Date functions delegate to dbt-core's cross-database macros rather than
reimplementing them — dbt maintains a correct implementation per adapter already,
and a second one here would be a second thing to keep right. What this toolkit
owns in those cases is the argument order, written out explicitly so the mapping
is visible in review.

## Adding another source dialect

The `sf_` prefix names the dialect the SQL came *from*. A BigQuery-origin project
gets a sibling `dbt-bigquery` toolkit with `bq_*` macros, added to `TOOLKITS` in
`pf/onboard/dialect.py` and to `macro-paths` in the scaffold template. Nothing
else changes — the report, the audit and the onboarder all read the toolkit list
rather than hardcoding one.

See `skills/port-snowflake-sql/` for the porting workflow.
