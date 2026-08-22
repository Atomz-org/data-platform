"""Production warehouses, declared once.

Development is DuckDB everywhere and is not negotiable — `PROJECT_TARGETS` in
`pf.scaffold.generator` makes `dev`, `ci` and `base` a local file, because a
developer who needs a warehouse account to run the project stops running the
project. This module is the other half: what `prod` becomes.

## Why a registry rather than a capability per warehouse

`snowflake` was a hand-written `Capability` with its profiles block, its env
vars, its plugin and its README inline. Adding BigQuery beside it meant copying
all four and keeping five copies of "development stays on DuckDB" in agreement
— and the copy that drifts is always the one nobody is currently reading.

So a warehouse declares only what is *different* about it: the dbt output block,
the credentials, the adapter package, and any prose the shared README cannot
know. `capability()` builds the rest, identically every time. Adding ClickHouse
is one `ProductionWarehouse` entry and no other edit.

Exactly one is default-enabled — Snowflake, because that is where this
platform's production runs. The others are `pf new-project --with bigquery` or
`pf capability-add redshift <group> <project>`, and switching an existing
project is the same command: `prod` is replaced in place and the DuckDB targets
beside it are not touched.

## What a warehouse does *not* get to change

Only the `prod` output. A capability that also moved `dev` would be a capability
that broke the laptop build, and the seam exists precisely so that cannot
happen by accident — `capability()` renders `PROJECT_TARGETS` with one key
swapped, and has no way to express anything else.

## Portability is claimed here and proved elsewhere

Declaring a BigQuery target does not make the models run on BigQuery. The `sf_*`
macros in `platform/toolkits/dbt-snowflake` dispatch per adapter, and
`pf align validate <group> <project> --stage dialect` is what says whether a
project is actually portable or merely untargeted. A warehouse entry without
that gate passing is a configuration, not a capability.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProductionWarehouse:
    """One engine `prod` can point at."""

    name: str
    title: str
    #: dbt adapter package, for the install hint and `pf doctor`.
    adapter: str
    #: The `prod` output block, verbatim, in the same shape as PROJECT_TARGETS.
    #: Values containing `{{` are emitted quoted by `render_target`, which is how
    #: `env_var` survives the YAML.
    output: dict[str, object]
    #: Credentials that must be set before `DBT_TARGET=prod` can connect. Only
    #: these are reported as missing; anything with a default in `output` is
    #: optional by construction.
    env: tuple[str, ...] = ()
    #: Claude Code plugins this warehouse's models need on.
    plugins: tuple[str, ...] = ()
    #: Extra prose for the generated README — the part the shared skeleton
    #: cannot know, like which auth mechanisms an engine supports.
    auth_note: str = ""
    #: Enabled without being asked for. Exactly one warehouse should set this.
    default_enabled: bool = False
    #: Anything an operator has to know that is neither credentials nor auth.
    caveats: tuple[str, ...] = field(default_factory=tuple)
    #: MCP server definition(s) for querying this warehouse directly, merged into
    #: the project's `.mcp.json` by `capability()`. Declared beside the dbt target
    #: for the same reason `om_connection` is: the engine dbt writes to and the
    #: engine an agent reads from must be the same engine, and two definitions in
    #: two files is how they end up not being.
    #:
    #: Credentials here are **not** added to `env`. That tuple is what `pf doctor`
    #: demands before `DBT_TARGET=prod` will connect, and a missing MCP token must
    #: not read as a broken warehouse — the models still build without it.
    mcp: dict[str, object] = field(default_factory=dict)
    #: OpenMetadata's connection `type` for this engine, and the config it
    #: expects. Declared beside the dbt target on purpose: a warehouse the
    #: platform can deploy to but not catalogue is half a warehouse, and keeping
    #: the two definitions apart is how they drift.
    #:
    #: The catalogue points at **production**, never at a developer's DuckDB
    #: file. That is not a limitation to work around — a catalogue of somebody's
    #: laptop is not a catalogue — and it is why these have no DuckDB
    #: counterpart.
    om_type: str = ""
    om_connection: dict[str, object] = field(default_factory=dict)


# `type` is dbt's adapter name and must match the installed dbt-<x> package.
# Every credential is an `env_var` call: this file is rendered into a project
# directory that is committed, so a literal here would be a committed secret.
# Values with a second argument have a default and are therefore optional.
WAREHOUSES: dict[str, ProductionWarehouse] = {
    "snowflake": ProductionWarehouse(
        name="snowflake",
        title="Snowflake",
        adapter="dbt-snowflake",
        output={
            "type": "snowflake",
            "account": "{{ env_var('SNOWFLAKE_ACCOUNT') }}",
            "user": "{{ env_var('SNOWFLAKE_USER') }}",
            "private_key_path": "{{ env_var('SNOWFLAKE_PRIVATE_KEY_PATH', '') }}",
            "password": "{{ env_var('SNOWFLAKE_PASSWORD', '') }}",
            "role": "{{ env_var('SNOWFLAKE_ROLE', 'SYSADMIN') }}",
            "warehouse": "{{ env_var('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH') }}",
            "database": "{{ env_var('SNOWFLAKE_DATABASE') }}",
            "schema": "{{ env_var('SNOWFLAKE_SCHEMA', 'ANALYTICS') }}",
            "threads": 8,
        },
        env=("SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_DATABASE"),
        plugins=("dbt-snowflake@platform",),
        auth_note=(
            "Authentication is key-pair by default — set "
            "`SNOWFLAKE_PRIVATE_KEY_PATH`. Set `SNOWFLAKE_PASSWORD` instead only "
            "if key-pair is not available to you; dbt uses whichever is present."
        ),
        default_enabled=True,
        om_type="Snowflake",
        om_connection={
            "type": "Snowflake",
            "account": "${SNOWFLAKE_ACCOUNT}",
            "username": "${SNOWFLAKE_USER}",
            "password": "${SNOWFLAKE_PASSWORD}",
            "role": "${SNOWFLAKE_ROLE}",
            "warehouse": "${SNOWFLAKE_WAREHOUSE}",
            "database": "${SNOWFLAKE_DATABASE}",
        },
    ),
    "bigquery": ProductionWarehouse(
        name="bigquery",
        title="BigQuery",
        adapter="dbt-bigquery",
        output={
            "type": "bigquery",
            # Service-account JSON on disk, referenced by path. `oauth` is the
            # other supported method and is a developer convenience; production
            # runs unattended, so the default is the one that works in CI.
            "method": "{{ env_var('BIGQUERY_METHOD', 'service-account') }}",
            "keyfile": "{{ env_var('BIGQUERY_KEYFILE', '') }}",
            "project": "{{ env_var('BIGQUERY_PROJECT') }}",
            "dataset": "{{ env_var('BIGQUERY_DATASET', 'analytics') }}",
            "location": "{{ env_var('BIGQUERY_LOCATION', 'US') }}",
            "priority": "interactive",
            "threads": 8,
        },
        env=("BIGQUERY_PROJECT",),
        auth_note=(
            "`BIGQUERY_METHOD=service-account` with `BIGQUERY_KEYFILE` pointing at "
            "the JSON key is the default. `BIGQUERY_METHOD=oauth` uses your "
            "`gcloud` application-default credentials and needs no keyfile — "
            "convenient locally, unavailable to an unattended run."
        ),
        caveats=(
            ("BigQuery has no `database`; `project` and `dataset` fill those "
             "roles, so a model that hardcodes a three-part name will not "
             "compile here."),
        ),
        om_type="BigQuery",
        om_connection={
            "type": "BigQuery",
            "credentials": {
                "gcpConfig": {"path": "${BIGQUERY_KEYFILE}"},
            },
            "billingProjectId": "${BIGQUERY_PROJECT}",
        },
    ),
    "redshift": ProductionWarehouse(
        name="redshift",
        title="Amazon Redshift",
        adapter="dbt-redshift",
        output={
            "type": "redshift",
            "host": "{{ env_var('REDSHIFT_HOST') }}",
            "port": "{{ env_var('REDSHIFT_PORT', '5439') | int }}",
            "user": "{{ env_var('REDSHIFT_USER') }}",
            "password": "{{ env_var('REDSHIFT_PASSWORD', '') }}",
            "dbname": "{{ env_var('REDSHIFT_DATABASE') }}",
            "schema": "{{ env_var('REDSHIFT_SCHEMA', 'analytics') }}",
            "sslmode": "require",
            "threads": 8,
        },
        env=("REDSHIFT_HOST", "REDSHIFT_USER", "REDSHIFT_DATABASE"),
        auth_note=(
            "Password auth via `REDSHIFT_PASSWORD`. For IAM auth set "
            "`method: iam` in the target and supply `REDSHIFT_IAM_PROFILE` — that "
            "is a deliberate edit, not a default, because IAM changes who the "
            "run authenticates *as*."
        ),
        caveats=(
            ("Redshift is case-insensitive and folds identifiers to lower case; "
             "a model relying on a quoted mixed-case column will resolve "
             "differently here than on DuckDB."),
        ),
        om_type="Redshift",
        om_connection={
            "type": "Redshift",
            "hostPort": "${REDSHIFT_HOST}:${REDSHIFT_PORT}",
            "username": "${REDSHIFT_USER}",
            "password": "${REDSHIFT_PASSWORD}",
            "database": "${REDSHIFT_DATABASE}",
        },
    ),
    "clickhouse": ProductionWarehouse(
        name="clickhouse",
        title="ClickHouse Cloud",
        adapter="dbt-clickhouse",
        output={
            "type": "clickhouse",
            "host": "{{ env_var('CLICKHOUSE_HOST') }}",
            "port": "{{ env_var('CLICKHOUSE_PORT', '8443') | int }}",
            "user": "{{ env_var('CLICKHOUSE_USER', 'default') }}",
            "password": "{{ env_var('CLICKHOUSE_PASSWORD', '') }}",
            "schema": "{{ env_var('CLICKHOUSE_DATABASE', 'analytics') }}",
            # ClickHouse Cloud is TLS-only on 8443. Defaulting these off would
            # produce a connection error that reads like bad credentials.
            "secure": True,
            "verify": True,
            "threads": 8,
        },
        env=("CLICKHOUSE_HOST", "CLICKHOUSE_PASSWORD"),
        auth_note=(
            "ClickHouse Cloud is TLS-only: port 8443 with `secure: true`. The "
            "`default` user is what a fresh service ships with — change "
            "`CLICKHOUSE_USER` once you have real roles."
        ),
        caveats=(
            ("dbt-clickhouse has no `merge` incremental strategy; models using "
             "it must move to `delete+insert` or `append` before this target "
             "will build."),
            ("ClickHouse calls a schema a database. `schema:` above is the "
             "ClickHouse database, which is why there is no separate "
             "`database` key."),
        ),
        om_type="Clickhouse",
        om_connection={
            "type": "Clickhouse",
            "hostPort": "${CLICKHOUSE_HOST}:${CLICKHOUSE_PORT}",
            "username": "${CLICKHOUSE_USER}",
            "password": "${CLICKHOUSE_PASSWORD}",
            "databaseSchema": "${CLICKHOUSE_DATABASE}",
            "https": True,
            "secure": True,
        },
    ),
}


def get(name: str) -> ProductionWarehouse:
    try:
        return WAREHOUSES[name]
    except KeyError:
        known = ", ".join(sorted(WAREHOUSES))
        raise KeyError(f"unknown production warehouse {name!r} — known: {known}") from None


def names() -> tuple[str, ...]:
    return tuple(sorted(WAREHOUSES))


def default_warehouse() -> ProductionWarehouse | None:
    """The one a project gets without asking. None if nothing is default."""
    for wh in WAREHOUSES.values():
        if wh.default_enabled:
            return wh
    return None
