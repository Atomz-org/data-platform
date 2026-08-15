---
name: port-snowflake-sql
description: Make SQL written for another warehouse run on this platform, using the portable sf_* macros. Use when onboarding a repo or adopting foreign SQL.
---
# Porting SQL from another warehouse

The goal is one set of models that runs on DuckDB in development and on the
production warehouse unchanged. Not a DuckDB copy of a Snowflake project — that
is two projects to keep in step, and they stop being in step immediately.

## Start with the report, not the SQL

```
pf dialect <path>
```

It reads every `.sql` in the tree and sorts the function calls into three piles.
Work them in this order, which is *not* the order they appear:

**1. `ambiguous` — first, and by hand.** These already resolve on the target and
mean something else by it. Nothing fails, so nothing tells you. `date_trunc`
takes `(part, date)` in Snowflake and DuckDB but `(date, part)` in BigQuery.
`least` and `greatest` return NULL in Snowflake if any argument is NULL, and skip
NULLs everywhere else. Establish which warehouse the SQL was written for before
touching a line, because the same text means different things depending on the
answer.

**2. `needs wrapping` — mechanical.** The target cannot resolve these, so the
build fails until they are wrapped. Loud, cheap, and safe to do quickly.

**3. `unsupported` — by hand.** No macro covers them. Either port the call site
or add a macro (see below).

## Wrapping a call site

Replace the raw call with its macro, quoting the arguments as SQL fragments:

```sql
-- before
select iff(status = 'paid', amount, 0) as paid_amount

-- after
select {{ sf_iff("status = 'paid'", 'amount', '0') }} as paid_amount
```

The arguments are strings because the macro pastes them into SQL. A bare
`amount` would be a Jinja variable that does not exist and renders empty, which
compiles to a syntax error rather than a wrong number — the good kind of failure.

For the NULL-sensitive pair, pass a list:

```sql
{{ sf_least(['first_seen_at', 'first_order_at']) }}
```

## What is already portable

Do not wrap what dbt-core already handles. `{{ dbt.date_trunc(...) }}`,
`{{ dbt.dateadd(...) }}` and friends are cross-database by construction, and
`pf dialect` correctly ignores them. If a call is already inside `{{ }}`, leave
it alone.

## Adding a macro

When `unsupported` names something real:

1. Add it to `platform/toolkits/dbt-snowflake/macros/`, in the file matching its
   kind. Use `adapter.dispatch` only where implementations genuinely differ —
   most compile to ANSI SQL every adapter already agrees on, and a dispatch there
   is indirection without portability.
2. Delegate to dbt-core if it has an equivalent, and **write the argument
   mapping out explicitly**. `dbt.datediff` takes the part last where Snowflake
   takes it first; that remap is the kind of thing that is obvious for a week.
3. Register it in `UNSUPPORTED` in `pf/onboard/dialect.py` so the report can
   recommend it.
4. Probe it in `platform/tests/test_toolkit_macros.py`. The test asserts the
   *source* dialect's answer, so where the two warehouses disagree, the
   disagreement is what gets pinned. A macro with no probe fails the suite.

## The rule that matters

Never translate a function whose semantics differ between dialects. A wrong
argument order compiles, runs, and returns a plausible number, and no review
catches it. Report it and let a human decide. Everything else in this toolkit is
downstream of that.

## Another source dialect

The `sf_` prefix is per source dialect, not per target. A BigQuery-origin project
gets a sibling `dbt-bigquery` toolkit with `bq_*` macros, added to `TOOLKITS` in
`dialect.py` and to `macro-paths` in the scaffold. Nothing else changes.
