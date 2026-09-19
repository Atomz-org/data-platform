# Production warehouse — DuckLake

**jaffle/jaffle-shop** develops on DuckDB and runs production on
DuckLake. One set of models serves both: the `sf_*` macros in
`platform/toolkits/dbt-snowflake` dispatch per adapter, so a model is written
once and compiles to whatever the *target* understands. `pf dialect` lists what
is covered, and `pf align validate jaffle jaffle-shop --stage dialect` is the
gate that says whether this project is actually portable or merely untested.

Declaring this target does not make the models run on DuckLake. That
gate passing is what does.

## Why development stays on DuckDB

A developer who needs a warehouse account to run the project stops running the
project. Every target but `prod` is a local DuckDB file, so `dbt build` works on
a laptop, offline, with no credentials, in seconds — and `base` exists so Recce
has a second state to diff against.

Only `prod` points at DuckLake. Nothing in this capability can move
`dev`, `ci` or `base`, by construction.

## Credentials

Read from the environment at run time and **never written to a file here** —
`transform/profiles.yml` holds `env_var` calls, not values, because it is
committed:

    required:  DUCKLAKE_METADATA
    optional:  DUCKLAKE_SCHEMA  DUCKLAKE_THREADS

`DUCKLAKE_METADATA` is the catalog: a path like `/lake/analytics.ducklake` (single writer), or a connection string like `postgres:dbname=lake host=...` (concurrent writers; DuckDB autoloads the postgres extension). Object-storage DATA_PATHs authenticate through DuckDB secrets or the standard AWS/GCS environment variables via httpfs — never a literal here.

`pf doctor` reports which are missing. Never paste one into a chat, a model
file, or this repository.

## Running against it

The adapter is an optional extra — nothing on a laptop needs it, because every
target but `prod` is DuckDB and dbt only loads the adapter the selected target
names.

```bash
uv sync --extra ducklake    # installs dbt-duckdb
DBT_TARGET=prod dbt build          # explicit, every time
pf align validate jaffle jaffle-shop --stage dialect
```

There is deliberately no shortcut. The target is named on every invocation
because the failure mode — believing you are on dev and being on prod — is worse
than the typing.

## What differs from DuckDB

- Same engine and dialect as dev, so the `pf align` dialect gate passes by construction — this is the one production target with zero portability distance from the laptop build.
- The parquet DATA_PATH is fixed when the lake is first created (`ATTACH 'ducklake:...' (DATA_PATH 's3://...')`, once, by an operator). Connecting afterwards reads it from the metadata; moving it is a data migration, not a config change. With no DATA_PATH given, files land in `<metadata>.files/` beside the catalog.
- A `.ducklake` file catalog resolves concurrent DDL by failing one side, and every dbt model is DDL — so `threads` defaults to 1 and the build is serial. With the metadata in Postgres, set `DUCKLAKE_THREADS` up; with a file catalog, leave it.
- OpenMetadata has no DuckLake connector yet, so this target is not catalogued; `om_type` is empty on purpose.

## Switching

```bash
pf capability-add <warehouse> jaffle jaffle-shop
```

`prod` is replaced in place; the DuckDB targets beside it, and anything you
hand-added to them, are left alone.
