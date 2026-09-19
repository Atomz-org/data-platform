"""The shared halves of housekeeping: what a task is, and which engine owns it.

Engine detection reads the project's committed profiles.yml rather than any
live connection, for the same reason `pf align` does: the file is the decision
record. Both lakehouse targets are `type: duckdb`, so the *type* cannot tell
them apart — DuckLake is the `ducklake:` path prefix, Iceberg is the attached
catalog whose options say `type: iceberg`. Anything else has an engine that
does its own housekeeping, and the answer for it is None, not a no-op plan.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Task:
    """One maintenance action, planned before anything runs.

    `sql` is what `--apply` executes, in order. A task with no SQL is not a
    failure to implement it — it is a capability the platform's connection
    genuinely does not have (R2's managed compaction, snapshot expiry on a
    catalog DuckDB cannot delete from), and `manual` says who does have it.
    """

    name: str
    reason: str
    sql: tuple[str, ...] = ()
    manual: str = ""

    @property
    def automated(self) -> bool:
        return bool(self.sql)


@dataclass(frozen=True)
class Report:
    """What `pf housekeeping` prints, and what a test can assert on."""

    engine: str
    group: str
    project: str
    tables: tuple[dict, ...] = ()
    tasks: tuple[Task, ...] = ()
    applied: tuple[str, ...] = ()
    notes: tuple[str, ...] = field(default_factory=tuple)


def retention_days(override: int | None = None) -> int:
    """Snapshot retention, in days. 7 keeps a week of time travel and diffs.

    One knob for both engines: a platform where DuckLake keeps a week and
    Iceberg keeps forever is a platform whose storage bill explains itself
    only to whoever set the two values apart.
    """
    if override is not None:
        return override
    return int(os.environ.get("PF_LAKE_RETENTION_DAYS", "7"))


def detect(profiles_text: str) -> str | None:
    """Which lakehouse the committed `prod` target points at, if any."""
    import yaml

    try:
        doc = yaml.safe_load(profiles_text) or {}
    except yaml.YAMLError:
        return None
    for value in doc.values():
        if not (isinstance(value, dict) and isinstance(value.get("outputs"), dict)):
            continue
        prod = value["outputs"].get("prod")
        if not isinstance(prod, dict) or prod.get("type") != "duckdb":
            return None
        if str(prod.get("path", "")).startswith("ducklake:"):
            return "ducklake"
        for entry in prod.get("attach") or []:
            options = entry.get("options") if isinstance(entry, dict) else None
            if isinstance(options, dict) and options.get("type") == "iceberg":
                return "iceberg"
        return None
    return None


def plan_for_project(group: str, project: str, project_dir: Path,
                     days: int | None = None) -> Report:
    """Inspect the project's lakehouse and plan its maintenance. Read-only."""
    from pf.housekeeping import ducklake, iceberg

    profiles = project_dir / "transform" / "profiles.yml"
    engine = detect(profiles.read_text()) if profiles.exists() else None
    if engine is None:
        return Report(engine="", group=group, project=project, notes=(
            ("prod is not a lakehouse target — its engine does its own "
             "housekeeping, and this command has nothing to add."),))

    mod = ducklake if engine == "ducklake" else iceberg
    con = mod.connect()
    try:
        tables, notes = mod.inspect(con)
        tasks = mod.plan(tables, retention_days(days))
    finally:
        con.close()
    return Report(engine=engine, group=group, project=project,
                  tables=tuple(tables), tasks=tuple(tasks), notes=tuple(notes))


def run(report: Report) -> Report:
    """Execute the automated tasks of a plan, in plan order.

    Order is load-bearing and the plan owns it: merging adjacent files writes
    a new snapshot, expiry must run after it so the pre-merge files become
    unreferenced, and cleanup must run last because it can only delete what
    nothing references any more.
    """
    from pf.housekeeping import ducklake, iceberg

    mod = ducklake if report.engine == "ducklake" else iceberg
    con = mod.connect()
    applied: list[str] = []
    try:
        for task in report.tasks:
            if not task.automated:
                continue
            for statement in task.sql:
                con.execute(statement)
            applied.append(task.name)
    finally:
        con.close()
    return Report(engine=report.engine, group=report.group, project=report.project,
                  tables=report.tables, tasks=report.tasks,
                  applied=tuple(applied), notes=report.notes)
