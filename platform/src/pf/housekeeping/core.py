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
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Task:
    """One maintenance action, planned before anything runs.

    `sql` is what `--apply` executes against a lakehouse, in order. `action`
    is the same thing for platform scope, where maintenance is file and API
    work rather than SQL — it returns a one-line detail for the report. A
    task with neither is not a failure to implement it — it is a capability
    the platform genuinely does not have (R2's managed compaction, snapshot
    expiry on a catalog DuckDB cannot delete from, a WAL that may belong to
    a live writer), and `manual` says who does have it.
    """

    name: str
    reason: str
    sql: tuple[str, ...] = ()
    action: Callable[[], str] | None = field(default=None, repr=False, compare=False)
    manual: str = ""

    @property
    def automated(self) -> bool:
        return bool(self.sql) or self.action is not None


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


def plan_platform(root: Path, days: int | None = None) -> Report:
    """Inspect the platform's own accumulation and plan its maintenance.

    The per-project command asks "is this project's lake healthy"; this asks
    the question nobody owns per project: Dagster's run history, every
    project's dbt log, the rendered reports and PR verdicts that are all
    regenerable and all only ever grow.
    """
    from pf.housekeeping import dagster_home, workspace

    days = ops_retention_days(days)
    tasks: list[Task] = []
    notes: list[str] = []
    for mod in (dagster_home, workspace):
        t, n = mod.plan(root, days)
        tasks.extend(t)
        notes.extend(n)
    return Report(engine="platform", group="", project="",
                  tasks=tuple(tasks), notes=tuple(notes))


def ops_retention_days(override: int | None = None) -> int:
    """Retention for run history and regenerable artefacts. Wider than the
    lake's snapshot retention: a two-week-old run record still answers "when
    did this start failing", which a snapshot that old rarely does."""
    if override is not None:
        return override
    return int(os.environ.get("PF_OPS_RETENTION_DAYS", "14"))


def run(report: Report) -> Report:
    """Execute the automated tasks of a plan, in plan order.

    Order is load-bearing and the plan owns it: merging adjacent files writes
    a new snapshot, expiry must run after it so the pre-merge files become
    unreferenced, and cleanup must run last because it can only delete what
    nothing references any more.
    """
    if report.engine == "platform":
        applied: list[str] = []
        details: list[str] = []
        for task in report.tasks:
            if task.action is None:
                continue
            details.append(task.action())
            applied.append(task.name)
        return Report(engine=report.engine, group=report.group,
                      project=report.project, tables=report.tables,
                      tasks=report.tasks, applied=tuple(applied),
                      notes=report.notes + tuple(details))

    from pf.housekeeping import ducklake, iceberg

    mod = ducklake if report.engine == "ducklake" else iceberg
    con = mod.connect()
    applied = []
    try:
        for task in report.tasks:
            if not task.sql:
                continue
            for statement in task.sql:
                con.execute(statement)
            applied.append(task.name)
    finally:
        con.close()
    return Report(engine=report.engine, group=report.group, project=report.project,
                  tables=report.tables, tasks=report.tasks,
                  applied=tuple(applied), notes=report.notes)
