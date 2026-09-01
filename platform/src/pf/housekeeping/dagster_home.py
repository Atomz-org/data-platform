"""Dagster housekeeping — run history is a database, not a log that rotates.

The local instance under `.dagster/` deletes nothing, ever: every run adds
rows to the SQLite run and event stores and a compute-log directory under
`storage/<run_id>/`. On a platform where every project's every build is a
run, the event log is the fastest-growing thing in the repository — and the
one whose growth shows up as a *slow Dagster UI*, which reads like an
orchestrator problem and is a retention problem.

Two tasks, both automated:

    prune_runs        delete run records (and their event rows) older than
                      retention — terminal states only, a run still queued or
                      started is never history
    sweep_compute_logs remove `storage/<run_id>/` directories whose run the
                      instance no longer knows — `delete_run` cleans the
                      database, not the filesystem, so these orphan quietly

Stack deployments (`pf stack`) keep runs in OpenMetadata's Postgres instead;
that retention belongs to the stack's own tooling, and this module says so
rather than reaching into a database it does not own.
"""

from __future__ import annotations

import os
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pf.housekeeping.core import Task

#: Run states that are history. Anything else is in flight and untouchable.
TERMINAL = ("SUCCESS", "FAILURE", "CANCELED")


def plan(root: Path, days: int) -> tuple[list[Task], list[str]]:
    home = root / ".dagster"
    if not (home / "dagster.yaml").exists():
        return [], ["no local Dagster home — nothing to prune"]
    notes = []
    if (root / ".dagster-stack").exists():
        notes.append("stack deployment detected: its runs live in Postgres — "
                     "prune there with the stack's own tooling, not here")
    cutoff = datetime.now(UTC) - timedelta(days=days)
    tasks = [
        Task(
            name="prune_dagster_runs",
            reason=f"terminal runs before {cutoff:%Y-%m-%d} — the event log "
                   f"grows per build and is why an old instance's UI drags",
            action=lambda: _prune_runs(home, cutoff),
        ),
        Task(
            name="sweep_compute_logs",
            reason="storage/<run_id>/ dirs for runs the instance no longer "
                   "knows — delete_run cleans the database, not the disk",
            action=lambda: _sweep_compute_logs(home),
        ),
    ]
    return tasks, notes


def _instance(home: Path):
    from dagster import DagsterInstance

    os.environ["DAGSTER_HOME"] = str(home.resolve())
    return DagsterInstance.get()


def _prune_runs(home: Path, cutoff: datetime) -> str:
    with _instance(home) as instance:
        return prune_records(instance, cutoff)


def prune_records(instance, cutoff: datetime) -> str:
    """Delete terminal run records older than cutoff. Split out so a test can
    hand in a fake instance — the decision logic is here, the SQLite is not."""
    from dagster import DagsterRunStatus, RunsFilter

    deleted = 0
    statuses = [DagsterRunStatus[s] for s in TERMINAL]
    while True:
        records = instance.get_run_records(
            filters=RunsFilter(statuses=statuses, created_before=cutoff),
            limit=100)
        if not records:
            break
        for record in records:
            instance.delete_run(record.dagster_run.run_id)
            deleted += 1
    return f"deleted {deleted} run record(s) before {cutoff:%Y-%m-%d}"


def _sweep_compute_logs(home: Path) -> str:
    storage = home / "storage"
    if not storage.is_dir():
        return "no storage/ directory"
    with _instance(home) as instance:
        removed = 0
        for entry in sorted(storage.iterdir()):
            # Run dirs are UUID-named; anything else in storage/ is not ours.
            if not entry.is_dir() or len(entry.name) != 36:
                continue
            if not instance.has_run(entry.name):
                shutil.rmtree(entry)
                removed += 1
    return f"removed {removed} orphaned compute-log dir(s)"
