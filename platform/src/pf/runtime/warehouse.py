"""Warehouse access. One DuckDB file per project — that is what makes sister
companies genuinely parallel, since DuckDB's single-writer lock is per file.

Every connection this module hands out communicates over ADBC and moves
results as Arrow (`pf.runtime.adbc`) — the duckdb Python DBAPI is not used
here. When a quack dev server owns the file (`pf quack serve` — see
`pf.runtime.quack`), readers reach the database over the wire instead of
opening the file, and writers take the write window. Both happen inside
`connect`, so callers are indifferent to whether the project is served.

Cross-entity reads go through `attach_sisters`, which mounts sibling databases
READ_ONLY so a roll-up can never corrupt a sister; a served sister's file is
borrowed for the duration, exactly as her own writers borrow it.

## MotherDuck is the same arrangement, in the cloud

Which means it has to stay one database per project. `PF_MOTHERDUCK_DB` names
the **account prefix**, never the database: the database a project opens is
`<prefix>_<project slug>`, built from the same slug that names the local file
and the Dagster writer pool.

It used to be the database name outright, and that is the defect this paragraph
exists to record. One exported variable — in a shell, a CI job, a Dagster
deployment — pointed every project in every group at a single MotherDuck
database. Two sisters then built their marts into the same tables, each
overwriting the other, and *nothing said so*: both runs report success, because
writing to the database you were configured to write to is not an error. The
per-file isolation above is load-bearing, and a shared `md:` target throws it
away while looking like configuration.

`PF_MOTHERDUCK_DATABASE` still names an exact database, for the case where
somebody genuinely means one — a migration, a scratch space, a single-tenant
deployment. It is deliberately the longer spelling and it is deliberately not
the variable anyone already has exported: sharing a database is now something
you ask for by name.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path

from pf.runtime import adbc, quack

EXTENSIONS = ("httpfs", "json")


def project_slug(project: str) -> str:
    """The one spelling of a project used as an identifier.

    The DuckDB file, the Dagster writer pool and the MotherDuck database are all
    named from this. A second convention would be a second answer to "which
    project is this", and the place that would surface is a cross-entity
    roll-up, where the two answers are both present and only one is right.
    """
    return project.replace("-", "_")


@dataclass(frozen=True)
class Warehouse:
    """Resolved warehouse handle for one project."""

    group: str
    project: str
    path: Path
    #: The **resolved** MotherDuck database, already tenant-scoped by
    #: `for_project` — never the raw `PF_MOTHERDUCK_DB` prefix. `dsn` prepends
    #: `md:` and nothing else, so whatever is here is what gets written to, and
    #: a handle can be printed and believed.
    motherduck: str | None = None

    @classmethod
    def for_project(cls, project_dir: str | Path, group: str, project: str) -> Warehouse:
        slug = project_slug(project)
        root = Path(project_dir)
        # Read here rather than in `dsn` so the scoping happens exactly once, at
        # the point where the project is known, and every later reader sees a
        # database name rather than an env var it has to re-interpret.
        #
        # Exact beats derived, and the prefix is suffixed rather than inspected:
        # a `PF_MOTHERDUCK_DB` that was holding a real database name before this
        # change now resolves to `<that>_<slug>`, which is visibly wrong on the
        # first run instead of quietly shared forever. The fix that error points
        # at is the right one — move the value to `PF_MOTHERDUCK_DATABASE`.
        exact = os.environ.get("PF_MOTHERDUCK_DATABASE")
        prefix = os.environ.get("PF_MOTHERDUCK_DB")
        md = exact or (f"{prefix}_{slug}" if prefix else None)
        return cls(
            group=group,
            project=project,
            path=root / "data" / f"{slug}.duckdb",
            motherduck=md,
        )

    @property
    def dsn(self) -> str:
        if self.motherduck:
            return f"md:{self.motherduck}"
        return str(self.path)

    @property
    def writer_pool(self) -> str:
        """Dagster concurrency pool — scoped per project so sisters never queue
        behind each other."""
        return f"duckdb_writer_{project_slug(self.project)}"

    def ensure_dir(self) -> Path:
        """Create `data/` so something else can open the file inside it.

        DuckDB creates the database but not the directory holding it, and
        `data/` is generated — gitignored, absent from every fresh checkout. Any
        writer that does not go through `connect()` has to call this first or it
        dies with `IO Error: Cannot open file`, which reads like a permissions
        or credentials fault and is neither. dbt and dlt are both such writers.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        return self.path

    @contextmanager
    def connect(self, read_only: bool = False) -> Iterator["adbc.Connection | quack.ReadConnection"]:
        self.ensure_dir()
        served = None if self.motherduck else quack.running_state(self.path)

        if served is not None and read_only:
            # The server holds the file's lock; the wire is not a preference
            # here, it is the only way in. Statements execute server-side, so
            # names resolve exactly as they would over a direct connection —
            # see `quack.ReadConnection` for why this is not an ATTACH.
            con = quack.read_connection(served)
            try:
                yield con
            finally:
                con.close()
            return

        with ExitStack() as stack:
            if served is not None:
                # A writer while served: borrow the file, give it back after.
                stack.enter_context(quack.write_window(self.path))
            if read_only and not self.path.exists():
                read_only = False
            con = adbc.connect(self.dsn, read_only=read_only)
            stack.callback(con.close)
            for ext in EXTENSIONS:
                # offline or already present — not fatal
                with suppress(Exception):
                    con.execute(f"INSTALL {ext}; LOAD {ext};")
            yield con

    @contextmanager
    def attach_sisters(self, sisters: dict[str, Path]) -> Iterator["adbc.Connection"]:
        """Attach sibling project databases READ_ONLY for cross-entity roll-ups.

        A served sister's file is borrowed for the duration — her server
        pauses and resumes, exactly as it does for her own writers. Attaching
        her endpoint instead would be prettier and is wrong today: a roll-up
        joins across catalogs in one statement, which the wire cannot carry,
        and the quack client cannot fetch schema-qualified base tables at all.

        Args:
            sisters: alias -> path of each sister's .duckdb file.
        """
        with ExitStack() as stack:
            for p in sisters.values():
                if quack.running_state(p) is not None:
                    stack.enter_context(quack.write_window(p))
            con = stack.enter_context(self.connect())
            for alias, p in sisters.items():
                if not Path(p).exists():
                    raise FileNotFoundError(f"sister database missing: {alias} at {p}")
                con.execute(f"ATTACH '{p}' AS {alias} (READ_ONLY)")
            try:
                yield con
            finally:
                for alias in sisters:
                    with suppress(Exception):
                        con.execute(f"DETACH {alias}")


def preview(con, table: str, limit: int = 5) -> dict:
    """Truncation policy in one place: schema + n rows + counts. Never a raw dump."""
    limit = min(limit, 20)
    cols = con.execute(f"DESCRIBE SELECT * FROM {table}").fetchall()
    rows = con.execute(f"SELECT * FROM {table} LIMIT {limit}").fetchall()
    total = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
    return {
        "table": table,
        "row_count": total,
        "columns": [{"name": c[0], "type": c[1]} for c in cols],
        "sample": [list(map(_scalar, r)) for r in rows],
        "truncated": total > limit,
    }


def _scalar(v):
    return v if v is None or isinstance(v, (int, float, bool, str)) else str(v)
