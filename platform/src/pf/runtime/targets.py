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

## A destination is per tenant; the credentials reaching it are not

`SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, `SNOWFLAKE_PASSWORD` describe *who is
connecting*. One estate has one set of them and exports them once, which is
correct and is left alone here. `schema` describes *where the build lands*, and
that is not the same kind of thing at all.

It used to be a shared constant — `ANALYTICS` on Snowflake, `analytics` on the
other four. With credentials exported once, as they are meant to be, acme-eu and
acme-us then built into the same schema, each dropping and recreating the
other's tables. Neither run failed: writing to the schema you were configured to
write to is not an error, so the only symptom is a mart whose numbers change
when a sister runs. So every destination default now carries `PROJECT_TOKEN` and
resolves to the project's own slug, and every credential stays exactly as shared
as it was.

An explicit env var still wins. These are two-argument `env_var` calls exactly
as before, so an estate that has already carved up its schemas by hand sets
`SNOWFLAKE_SCHEMA` and nothing here argues — the change is to what happens when
nobody sets it, which is where the collision lived.

Existing projects are unaffected. `transform/profiles.yml` is seeded once and
then hand-maintained, and nothing rewrites a `prod` block already pointing at a
real warehouse; this changes what a *new* render produces and what an unset
variable resolves to.

## Portability is claimed here and proved elsewhere

Declaring a BigQuery target does not make the models run on BigQuery. The `sf_*`
macros in `platform/toolkits/dbt-snowflake` dispatch per adapter, and
`pf align validate <group> <project> --stage dialect` is what says whether a
project is actually portable or merely untargeted. A warehouse entry without
that gate passing is a configuration, not a capability.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: The placeholder a destination default carries until a project resolves it.
#:
#: `{{module}}` is the *scaffolder's* token, not dbt's. Every file a capability
#: writes goes through `pf.scaffold.generator.render`, which substitutes it with
#: the project's module slug, and `transform/profiles.yml` is written through
#: exactly that path — so `'ANALYTICS_{{module}}'` reaches disk as
#: `ANALYTICS_acme_eu` and dbt never sees a brace. Reusing the token the
#: scaffolder already resolves is what keeps this file free of a project
#: parameter it would otherwise have to thread through `WAREHOUSES`, which is a
#: module-level constant built before any project exists.
#:
#: It appears in the dbt `output` block and nowhere else. `om_connection` is
#: serialised straight to YAML by `pf.tools.openmetadata` with no render pass,
#: so a token there would be written verbatim into a workflow file — which is
#: why the catalogue keeps taking its database from the env var alone.
#:
#: A caller that writes a target *without* going through `render` must resolve
#: it first with `ProductionWarehouse.output_for`.
PROJECT_TOKEN = "{{module}}"


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
    #:
    #: The destination key — `schema`, or `dataset` on BigQuery — carries
    #: `PROJECT_TOKEN` in its default. Read it through `output_for` whenever the
    #: project is known; read it raw only to write through a renderer that
    #: resolves the token itself.
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

    def output_for(self, project: str) -> dict[str, object]:
        """`output` with `PROJECT_TOKEN` resolved for one project.

        The slug convention is `pf.runtime.warehouse.project_slug` — the same
        one that names the project's DuckDB file and its Dagster writer pool.
        Spelled out here rather than imported because `pf.runtime.warehouse`
        pulls in duckdb at import time and this module is read by the CLI on
        every invocation, including the ones that never open a database.

        Non-string values — `threads: 8`, `secure: True` — are passed through
        untouched, because `render_target` distinguishes them and a stringified
        `True` would reach the YAML as something nobody can copy.
        """
        slug = project.replace("-", "_")
        return {
            key: value.replace(PROJECT_TOKEN, slug) if isinstance(value, str) else value
            for key, value in self.output.items()
        }


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
            # `ANALYTICS` alone put every project that shares an account in one
            # schema. The prefix is kept because it is what a Snowflake operator
            # expects to see; the tenant half arrives lower-case because the
            # scaffolder's slug is, and that is harmless — dbt-snowflake quotes
            # nothing by default, so Snowflake folds the whole unquoted
            # identifier and `ANALYTICS_acme_eu` resolves as
            # `ANALYTICS_ACME_EU`.
            "schema": "{{ env_var('SNOWFLAKE_SCHEMA', 'ANALYTICS_{{module}}') }}",
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
            # The dataset is BigQuery's tenant boundary here: `project` is a
            # billing and IAM decision an estate usually makes once, so a shared
            # `analytics` dataset underneath it is two sisters in one namespace.
            "dataset": "{{ env_var('BIGQUERY_DATASET', 'analytics_{{module}}') }}",
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
            # Lower-case on purpose: Redshift folds identifiers down, so a
            # tenant-scoped schema written any other way comes back different
            # from how it went in.
            "schema": "{{ env_var('REDSHIFT_SCHEMA', 'analytics_{{module}}') }}",
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
    "databricks": ProductionWarehouse(
        name="databricks",
        title="Databricks",
        adapter="dbt-databricks",
        output={
            "type": "databricks",
            # Workspace hostname with no scheme and no trailing slash. On Azure
            # that is `adb-<workspace-id>.<n>.azuredatabricks.net`; the adapter
            # prepends https itself and rejects a value that already has it.
            "host": "{{ env_var('DATABRICKS_HOST') }}",
            # A SQL warehouse, not a cluster: `/sql/1.0/warehouses/<id>`.
            # All-purpose clusters also work and cost several times as much to
            # keep warm, which is why the documented form is the warehouse one.
            "http_path": "{{ env_var('DATABRICKS_HTTP_PATH') }}",
            "token": "{{ env_var('DATABRICKS_TOKEN', '') }}",
            # OAuth machine-to-machine, for a service principal. Present so the
            # switch is an env change rather than a profile edit; see auth_note.
            "client_id": "{{ env_var('DATABRICKS_CLIENT_ID', '') }}",
            "client_secret": "{{ env_var('DATABRICKS_CLIENT_SECRET', '') }}",
            # Unity Catalog's first level. dbt's `database` is this, which is
            # why the key is spelled `catalog` and there is no `database`.
            "catalog": "{{ env_var('DATABRICKS_CATALOG') }}",
            # The catalog is where an estate draws its access boundary, so it
            # stays whatever the operator set. The schema below it is the
            # project, which is also the level Unity Catalog grants and lineage
            # read most naturally.
            "schema": "{{ env_var('DATABRICKS_SCHEMA', 'analytics_{{module}}') }}",
            "threads": 8,
        },
        env=("DATABRICKS_HOST", "DATABRICKS_HTTP_PATH", "DATABRICKS_CATALOG"),
        auth_note=(
            "A personal access token in `DATABRICKS_TOKEN` is the default, "
            "because it works identically on all three clouds and in CI. For an "
            "unattended production run prefer OAuth M2M: create a service "
            "principal, then set `DATABRICKS_CLIENT_ID` and "
            "`DATABRICKS_CLIENT_SECRET` and leave the token unset — the adapter "
            "uses whichever pair is present. Tokens carry a human's "
            "entitlements and expire on a schedule nobody owns; a service "
            "principal does not."
        ),
        caveats=(
            ("Unity Catalog is a three-level namespace — `catalog.schema.table`. "
             "dbt's `database` is the catalog, so a model that hardcodes a "
             "two-part name resolves against the wrong level here, and one "
             "written for DuckDB's `database.schema` will not compile at all."),
            ("A SQL warehouse auto-stops when idle. The first build after a "
             "quiet period pays a cold start of a minute or more, which reads "
             "as a hung run rather than a slow one — set the warehouse's "
             "auto-stop deliberately rather than discovering it in CI."),
            ("This is the one target that is genuinely the same on AWS, Azure "
             "and GCP. Only `host` differs between them, so a project that "
             "builds here builds on all three — which is the reason to choose "
             "it over Fabric or Synapse if Azure is not the only destination."),
        ),
        om_type="Databricks",
        om_connection={
            "type": "Databricks",
            "hostPort": "${DATABRICKS_HOST}:443",
            "token": "${DATABRICKS_TOKEN}",
            "httpPath": "${DATABRICKS_HTTP_PATH}",
            "catalog": "${DATABRICKS_CATALOG}",
            "useUnityCatalog": True,
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
            # ClickHouse calls this a database (see the caveat below), which
            # makes it this engine's whole namespace — there is no level above
            # it to separate two projects, so the tenant has to be in here.
            "schema": "{{ env_var('CLICKHOUSE_DATABASE', 'analytics_{{module}}') }}",
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
