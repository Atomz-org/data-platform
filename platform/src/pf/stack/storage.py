"""Dagster's storage, on OpenMetadata's Postgres, in its own schema.

## Why one database and not two

Dagster shipped on SQLite under `DAGSTER_HOME`. That is a file, so it is a file
per machine: the container and the host disagreed about which runs had happened,
and every `podman rm` lost the run history. OpenMetadata already runs a Postgres
beside it. A second Postgres for eight projects' run logs is a second thing to
back up, a second thing to upgrade, and a second thing to be down.

So: one database, `openmetadata_db`, with the two systems separated by *schema*
rather than by server.

    public    OpenMetadata's ~200 tables. Untouched — it was there first and
              its Flyway migrations assume they own it.
    dagster   Dagster's runs, events, schedules, ticks. Owned by a `dagster`
              role that has no rights in `public`.

Recce gets no schema. It has no server-side database at all — a review is a
`recce_state.json`, and since `pf artifacts` those live in R2. Nothing to merge.

## How the schema is selected

Dagster has no schema setting. It has `params`, which are urlencoded onto the
libpq connection string, and libpq accepts `options`:

    postgresql://dagster:...@host:5432/openmetadata_db?options=-c%20search_path%3Ddagster

Every unqualified `CREATE TABLE` alembic issues then lands in `dagster`. This is
load-bearing and invisible: drop the param and Dagster's migrations run happily
against `public`, interleaving its tables with OpenMetadata's, and the damage is
only obvious at the next OpenMetadata upgrade.

`search_path` does not create the schema. `pf stack db-init` does, once, as an
admin role — see `ensure_schema`.

## Why the block is spliced rather than the file generated

`.dagster/dagster.yaml` is hand-written and carries the pool commentary that
explains why sisters do not collide on DuckDB's writer lock. Generating the
whole file would throw that away on the first render. So this module owns
exactly the lines between two markers and nothing else, the same way
`pf.scaffold.generator.replace_target` owns one dbt output block.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

#: Environment the storage block reads. `dagster.yaml` refers to these by name
#: rather than by value: the file is tracked, and a rendered password would be a
#: password in git.
ENV_HOST = "PF_STACK_PG_HOST"
ENV_PORT = "PF_STACK_PG_PORT"
ENV_DB = "PF_STACK_PG_DB"
ENV_USER = "PF_STACK_PG_USER"
ENV_PASSWORD = "PF_STACK_PG_PASSWORD"
ENV_SCHEMA = "PF_STACK_PG_SCHEMA"

#: Admin credentials, used once by `pf stack db-init` and never by Dagster.
ENV_ADMIN_USER = "PF_STACK_PG_ADMIN_USER"
ENV_ADMIN_PASSWORD = "PF_STACK_PG_ADMIN_PASSWORD"

DEFAULT_DB = "openmetadata_db"
DEFAULT_SCHEMA = "dagster"
DEFAULT_USER = "dagster"
DEFAULT_PORT = 5432

BEGIN = "# >>> pf stack: storage"
END = "# <<< pf stack: storage"


@dataclass(frozen=True)
class Settings:
    """Where Dagster's storage lives."""

    host: str
    db: str = DEFAULT_DB
    user: str = DEFAULT_USER
    #: `repr=False` for the same reason `pf.artifacts.Store` hides its secret: a
    #: traceback prints the frame's locals, and a connection failure is exactly
    #: when this object gets printed.
    password: str = field(default="", repr=False)
    port: int = DEFAULT_PORT
    schema: str = DEFAULT_SCHEMA

    @property
    def dsn(self) -> str:
        """libpq URI, schema-scoped. For `db-init` and `pf stack status`."""
        from urllib.parse import quote

        auth = quote(self.user, safe="")
        if self.password:
            auth += ":" + quote(self.password, safe="")
        opts = quote(f"-c search_path={self.schema}", safe="")
        return (f"postgresql://{auth}@{self.host}:{self.port}/{self.db}"
                f"?options={opts}")


def settings(env: dict[str, str] | None = None) -> Settings | None:
    """Read the environment, or None when Postgres storage is not configured.

    None is not an error. A laptop with no stack running should keep the SQLite
    instance it has always had — `pf stack render` removes the block rather than
    writing one that points at a host nobody is serving, because a `dagster.yaml`
    naming an unreachable Postgres fails at *import*, taking every code location
    down with it.
    """
    e = env if env is not None else dict(os.environ)
    host = (e.get(ENV_HOST) or "").strip()
    if not host:
        return None
    port = (e.get(ENV_PORT) or "").strip()
    return Settings(
        host=host,
        db=(e.get(ENV_DB) or "").strip() or DEFAULT_DB,
        user=(e.get(ENV_USER) or "").strip() or DEFAULT_USER,
        password=e.get(ENV_PASSWORD) or "",
        port=int(port) if port.isdigit() else DEFAULT_PORT,
        schema=(e.get(ENV_SCHEMA) or "").strip() or DEFAULT_SCHEMA,
    )


def admin_settings(s: Settings, env: dict[str, str] | None = None) -> Settings:
    """`s` with the admin role substituted, for schema creation."""
    e = env if env is not None else dict(os.environ)
    return Settings(
        host=s.host,
        db=s.db,
        user=(e.get(ENV_ADMIN_USER) or "").strip() or "postgres",
        password=e.get(ENV_ADMIN_PASSWORD) or "",
        port=s.port,
        # Admin work is DDL against a named schema; it must not inherit a
        # search_path pointing at a schema that does not exist yet.
        schema="public",
    )


def storage_block(s: Settings) -> str:
    """The `storage:` mapping, marker to marker."""
    return "\n".join([
        BEGIN,
        "# Rendered by `pf stack render`. Values come from the environment so",
        "# that this tracked file never carries the password.",
        "#",
        f"# `options` is what puts the tables in the `{s.schema}` schema instead",
        "# of `public`, where OpenMetadata's own ~200 tables live. Removing it",
        "# does not fail; it interleaves two products in one namespace.",
        "storage:",
        "  postgres:",
        "    postgres_db:",
        f"      hostname:\n        env: {ENV_HOST}",
        f"      username:\n        env: {ENV_USER}",
        f"      password:\n        env: {ENV_PASSWORD}",
        f"      db_name:\n        env: {ENV_DB}",
        f"      port:\n        env: {ENV_PORT}",
        "      params:",
        f"        options: -c search_path={s.schema}",
        END,
    ])


def merge_storage(text: str, s: Settings | None) -> tuple[str, bool]:
    """Splice the storage block into `dagster.yaml`; return (text, changed).

    Idempotent in both directions: rendering twice is a no-op, and rendering
    with `None` removes the block so the instance falls back to SQLite. Anything
    outside the markers is returned byte for byte.
    """
    lines = text.splitlines()
    try:
        start = lines.index(BEGIN)
        end = lines.index(END, start)
        before, after = lines[:start], lines[end + 1:]
    except ValueError:
        before, after = lines, []
        # A trailing blank line before an appended block, but only one, and only
        # when there is something to separate it from.
        while before and not before[-1].strip():
            before.pop()
        if before:
            before.append("")

    body = storage_block(s).splitlines() if s else []
    if not body:
        while after and not after[0].strip():
            after.pop(0)
        while before and not before[-1].strip():
            before.pop()

    out = "\n".join([*before, *body, *after]).rstrip("\n") + "\n"
    return out, out != text


def write(home: Path, s: Settings | None, *,
          base: Path | None = None) -> tuple[Path, bool]:
    """Write `<home>/dagster.yaml` as `base` plus the storage block.

    `base` is the tracked `.dagster/dagster.yaml`, and it is re-read on every
    render rather than copied once. The stack runs with its own DAGSTER_HOME —
    otherwise the container, which has Postgres, and the host, which does not,
    would take turns adding and removing the block from a tracked file — and a
    one-time copy would mean the pool limits that keep sisters off each other's
    DuckDB writer lock silently stop tracking the file that documents them.

    When `home` *is* the base directory the operation is a plain in-place
    merge, because `merge_storage` only ever touches its own markers.
    """
    path = home / "dagster.yaml"
    source = base if base and base != path and base.exists() else path
    text = source.read_text() if source.exists() else ""
    merged, _ = merge_storage(text, s)
    home.mkdir(parents=True, exist_ok=True)
    current = path.read_text() if path.exists() else ""
    changed = merged != current
    if changed:
        path.write_text(merged)
    return path, changed


# ------------------------------------------------------------------- init --
def ensure_schema(s: Settings, admin: Settings) -> list[str]:
    """Create the role and the schema. Idempotent; returns what it did.

    Runs as `admin` because `CREATE ROLE` is a superuser act, and connects to
    `s.db` because a schema belongs to a database. Grants are deliberately
    narrow: `dagster` gets its own schema and `CONNECT`, and nothing at all in
    `public` — the whole point of the split is that a Dagster migration cannot
    reach OpenMetadata's tables.
    """
    import psycopg2  # dagster-postgres brings it; import here so `pf` still
    from psycopg2 import sql  # imports on a checkout without the extra.

    done: list[str] = []
    conn = psycopg2.connect(admin.dsn)
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("select 1 from pg_roles where rolname = %s", (s.user,))
            if cur.fetchone():
                done.append(f"role {s.user} exists")
                if s.password:
                    cur.execute(
                        sql.SQL("alter role {} with password %s").format(
                            sql.Identifier(s.user)), (s.password,))
                    done.append("password reset")
            else:
                cur.execute(
                    sql.SQL("create role {} with login password %s").format(
                        sql.Identifier(s.user)), (s.password,))
                done.append(f"role {s.user} created")

            cur.execute("select 1 from information_schema.schemata "
                        "where schema_name = %s", (s.schema,))
            existed = bool(cur.fetchone())
            cur.execute(
                sql.SQL("create schema if not exists {} authorization {}").format(
                    sql.Identifier(s.schema), sql.Identifier(s.user)))
            done.append(f"schema {s.schema} " + ("exists" if existed else "created"))

            cur.execute(sql.SQL("grant connect on database {} to {}").format(
                sql.Identifier(s.db), sql.Identifier(s.user)))
            cur.execute(sql.SQL("grant all on schema {} to {}").format(
                sql.Identifier(s.schema), sql.Identifier(s.user)))
            done.append("grants applied")
    finally:
        conn.close()
    return done


def table_counts(s: Settings) -> dict[str, int]:
    """Tables per schema, as the connecting role can see them.

    `pf stack status` reports this because the failure it is looking for is
    silent: Dagster running against `public` looks exactly like Dagster running
    against `dagster`, until the row counts are compared.
    """
    import psycopg2

    conn = psycopg2.connect(s.dsn)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "select table_schema, count(*) from information_schema.tables "
                "where table_schema not in ('pg_catalog', 'information_schema') "
                "group by 1 order by 1")
            return {row[0]: int(row[1]) for row in cur.fetchall()}
    finally:
        conn.close()
