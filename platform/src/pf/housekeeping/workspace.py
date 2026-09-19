"""Workspace housekeeping — regenerable artefacts that only ever grow.

Everything this module touches can be rebuilt by the tool that wrote it,
which is the admission test for automation here: dbt rewrites its log on the
next run, `edr report` re-renders in full, `pf pr report` regenerates a PR's
JSON on demand. What canNOT be rebuilt is never touched — `provenance/` is
append-only by design and gate-denied besides, warehouse *data* belongs to
the lakehouse scope, and a `.duckdb.wal` is somebody's un-checkpointed
writes, so it gets an instruction, not a deletion.

Automated:
    truncate_dbt_logs   per-project transform/logs/dbt.log over the size cap
    prune_pr_reports    data/pr/*.json older than retention
    prune_edr_reports   rendered Elementary reports older than retention

Report-only:
    stray write-ahead logs beside the dev warehouses — a WAL beside a closed
    database is a crashed writer's last state; *opening* the database replays
    and checkpoints it, deleting it discards those writes. Only a person
    knows which one they want.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from pf.housekeeping.core import Task


def _log_cap_mb() -> int:
    return int(os.environ.get("PF_HOUSEKEEPING_LOG_MB", "64"))


def plan(root: Path, days: int) -> tuple[list[Task], list[str]]:
    tasks: list[Task] = []
    notes: list[str] = []
    horizon = time.time() - days * 86400

    cap = _log_cap_mb()
    logs = [p for p in sorted(root.glob("groups/*/projects/*/transform/logs/dbt.log"))
            if p.stat().st_size > cap * 1_000_000]
    if logs:
        tasks.append(Task(
            name="truncate_dbt_logs",
            reason=f"{len(logs)} dbt log(s) over {cap} MB "
                   f"({', '.join(p.parts[-4] for p in logs)}) — dbt rewrites "
                   f"the file on its next run",
            action=lambda paths=tuple(logs): _truncate(paths),
        ))

    pr_dir = root / "data" / "pr"
    old_pr = [p for p in sorted(pr_dir.glob("*.json"))
              if p.stat().st_mtime < horizon] if pr_dir.is_dir() else []
    if old_pr:
        tasks.append(Task(
            name="prune_pr_reports",
            reason=f"{len(old_pr)} PR report(s) older than {days} day(s) — "
                   f"`pf pr report` regenerates any of them on demand",
            action=lambda paths=tuple(old_pr): _delete(paths),
        ))

    old_edr = [p for p in sorted(root.glob("groups/*/projects/*/transform/edr_target/*"))
               if p.is_file() and p.stat().st_mtime < horizon]
    if old_edr:
        tasks.append(Task(
            name="prune_edr_reports",
            reason=f"{len(old_edr)} rendered Elementary file(s) older than "
                   f"{days} day(s) — `edr report` re-renders in full",
            action=lambda paths=tuple(old_edr): _delete(paths),
        ))

    wals = sorted(root.glob("groups/*/projects/*/data/*.duckdb.wal"))
    if wals:
        tasks.append(Task(
            name="checkpoint_stray_wals",
            reason=f"{len(wals)} write-ahead log(s) beside a dev warehouse "
                   f"({', '.join(p.parts[-4] for p in wals)}) — a crashed "
                   f"writer's un-checkpointed state",
            manual="open each database once (`duckdb <path>`) to replay and "
                   "checkpoint the WAL — deleting it instead discards those "
                   "writes, and only you know whether they matter.",
        ))

    sizes = sorted(root.glob("groups/*/projects/*/data/*.duckdb"))
    if sizes:
        total = sum(p.stat().st_size for p in sizes) / 1e9
        notes.append(f"{len(sizes)} dev warehouse(s), {total:.1f} GB total — "
                     f"space freed by dropped tables is reclaimed on rebuild "
                     f"(`pf seed`), not by deletion inside the file")
    return tasks, notes


def _truncate(paths: tuple[Path, ...]) -> str:
    for p in paths:
        p.write_text("")
    return f"truncated {len(paths)} dbt log(s)"


def _delete(paths: tuple[Path, ...]) -> str:
    for p in paths:
        p.unlink(missing_ok=True)
    return f"deleted {len(paths)} file(s)"
