# Stage 3 — one SQL, two targets

**Goal condition:** the same models compile on DuckDB in development and on the
production warehouse, and mean the same thing on both.

Development is DuckDB because a developer who needs a warehouse account to run
the project stops running the project. Production is whatever the business
actually runs. **There are not two copies of the SQL.** A per-warehouse fork is
the same model twice, and the copies diverge on the first bug fix.

## Evaluate

```bash
pf align evaluate <group> <project> --stage dialect
pf dialect <path>                       # standalone, any tree of SQL
```

### The two failure classes are not equally dangerous

| Class | What happens | Cost |
|---|---|---|
| **unsupported / needs wrapping** | dbt stops, someone reads the error | minutes |
| **ambiguous** | it compiles, runs, and returns a different number | a dashboard |

`iff`, `nvl`, `div0`, `charindex` do not exist in DuckDB — the build fails and
says so. That is the cheap class.

The expensive class is the one that works. `least(1, NULL)` is `NULL` in
Snowflake and `1` in DuckDB. `datediff` takes `(part, start, end)` in Snowflake
and `(start, end, part)` in dbt's cross-database macro. `date_trunc` takes
`(part, date)` in DuckDB and Snowflake and `(date, part)` in BigQuery. Every one
of those parses cleanly on both sides and quietly means something else.

**Give the ambiguous findings the attention.** They are already running, and they
can already be wrong.

## Implement

Wrap each call site in its portable macro from
`platform/toolkits/dbt-snowflake`:

```sql
-- before                              -- after
iff(x > 0, 'yes', 'no')                {{ sf_iff('x > 0', "'yes'", "'no'") }}
div0(a, b)                             {{ sf_div0('a', 'b') }}
datediff('day', a, b)                  {{ sf_datediff('day', 'a', 'b') }}
least(a, b)                            {{ sf_least(['a', 'b']) }}
```

`pf dialect` prints the macro for each finding. The macros use
`adapter.dispatch`, so one call compiles to whatever the *target* understands —
and they pin the **source dialect's** semantics everywhere, which is the point:
`sf_least(1, NULL)` is `NULL` on DuckDB too.

Three deliberately differ from the DuckDB native function. Do not "fix" them:

| Macro | Returns | Native DuckDB |
|---|---|---|
| `sf_least(1, NULL)` | `NULL` | `1` |
| `sf_div0(1, 0)` | `0` | error |
| `sf_safe_divide(1, 0)` | `NULL` | error |

If a function has no macro, add one to the toolkit and register it in
`pf/onboard/dialect.py` — **from a platform session, not a project one.** From a
project session it is a finding to report.

### The targets

```bash
pf capability-add snowflake <group> <project>
```

Writes a `prod` target reading credentials from the environment. No credential is
read, stored or asked for. `dev`, `ci` and `base` stay on DuckDB.

`base` exists so Recce has a second state to diff against later — same DuckDB
file, different schema.

## Validate

```bash
pf align validate <group> <project> --stage dialect
```

Conditions: nothing unresolvable, nothing ambiguous, `dev`/`base`/`prod` declared
with the expected types, the toolkit on `macro-paths`, and `dbt parse` clean.

`dbt parse` proves it compiles. It does **not** prove production agrees with
development — nothing here can, without credentials. When they arrive, the proof
is a `dbt build` on both targets and a Recce diff between them, which is the
review stage's job.

## Then

The layers stage. Do not start it while `dbt parse` is red — every layer finding
depends on a manifest.
