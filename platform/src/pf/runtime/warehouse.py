"""Warehouse access. One DuckDB file per project — that is what makes sister
companies genuinely parallel, since DuckDB's single-writer lock is per file.

Cross-entity reads go through `attach_sisters`, which mounts sibling databases
READ_ONLY so a roll-up can never corrupt a sister.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import duckdb

EXTENSIONS = ("httpfs", "json")


@dataclass(frozen=True)
class Warehouse:
    """Resolved warehouse handle for one project."""

    group: str
    project: str
    path: Path
    motherduck: str | None = None

    @classmethod
    def for_project(cls, project_dir: str | Path, group: str, project: str) -> "Warehouse":
        root = Path(project_dir)
        md = os.environ.get("PF_MOTHERDUCK_DB")
        return cls(
            group=group,
            project=project,
            path=root / "data" / f"{project.replace('-', '_')}.duckdb",
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
        return f"duckdb_writer_{self.project.replace('-', '_')}"

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
    def connect(self, read_only: bool = False) -> Iterator[duckdb.DuckDBPyConnection]:
        self.ensure_dir()
        if read_only and not self.path.exists():
            read_only = False
        con = duckdb.connect(self.dsn, read_only=read_only)
        try:
            for ext in EXTENSIONS:
                try:
                    con.execute(f"INSTALL {ext}; LOAD {ext};")
                except duckdb.Error:
                    pass  # offline or already present — not fatal
            yield con
        finally:
            con.close()

    @contextmanager
    def attach_sisters(self, sisters: dict[str, Path]) -> Iterator[duckdb.DuckDBPyConnection]:
        """Attach sibling project databases READ_ONLY for cross-entity roll-ups.

        Args:
            sisters: alias -> path of each sister's .duckdb file.
        """
        with self.connect() as con:
            for alias, p in sisters.items():
                if not Path(p).exists():
                    raise FileNotFoundError(f"sister database missing: {alias} at {p}")
                con.execute(f"ATTACH '{p}' AS {alias} (READ_ONLY)")
            try:
                yield con
            finally:
                for alias in sisters:
                    try:
                        con.execute(f"DETACH {alias}")
                    except duckdb.Error:
                        pass


def preview(con: duckdb.DuckDBPyConnection, table: str, limit: int = 5) -> dict:
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
