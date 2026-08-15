# Production warehouse — Snowflake

**jaffle/jaffle-shop** develops on DuckDB and runs production on Snowflake.
One set of models serves both: the `sf_*` macros in
`platform/toolkits/dbt-snowflake` dispatch per adapter, so a model is written
once and compiles to whatever the *target* understands. `pf dialect` lists what
is covered, and `pf align validate jaffle jaffle-shop --stage dialect` is the
gate that says whether this project is actually portable or merely untested.

## Why development stays on DuckDB

A developer who needs a warehouse account to run the project stops running the
project. Every target but `prod` is a local DuckDB file, so `dbt build` works on
a laptop, offline, with no credentials, in seconds — and `base` exists so Recce
has a second state to diff against.

## Credentials

Read from the environment at run time and **never written to a file here**:

    SNOWFLAKE_ACCOUNT   SNOWFLAKE_USER    SNOWFLAKE_ROLE
    SNOWFLAKE_WAREHOUSE SNOWFLAKE_DATABASE SNOWFLAKE_SCHEMA

Authentication is key-pair by default — set `SNOWFLAKE_PRIVATE_KEY_PATH`. Set
`SNOWFLAKE_PASSWORD` instead only if key-pair is not available to you; dbt uses
whichever is present. `pf doctor` reports which are missing. Never paste one into
a chat, a model file, or this repository.

## Running against it

```bash
DBT_TARGET=prod dbt build          # explicit, every time
pf align validate jaffle jaffle-shop --stage dialect
```

There is deliberately no shortcut. The target is named on every invocation
because the failure mode — believing you are on dev and being on prod — is worse
than the typing.
