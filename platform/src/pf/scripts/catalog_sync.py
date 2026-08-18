#!/usr/bin/env python3
"""Refresh everything derived from a build: graph, topology, catalogue.

Run this after dbt or dlt has moved data. It is the one place that answers
"the warehouse changed — what else is now stale?", and the answer is always the
same list, so it lives here once instead of in a Dagster asset, a CI step and
somebody's shell history.

    dlt / dbt run
        │
        ├─ knowledge graph      kg_search, impact analysis, the PreToolUse gate
        ├─ context card         the always-on index every agent session loads
        ├─ MDL manifest         the semantic layer BI reads
        ├─ OWL export           the formal ontology
        ├─ otop manifest        policy and evidence as an OpenTopology graph
        └─ OpenMetadata         glossary, role tags, metrics, tables, columns

## Three ways to run it, one implementation

    python -m pf.scripts.catalog_sync acme acme-eu           # standalone
    uv run pf catalog sync acme acme-eu                      # through the CLI
    <catalog_sync asset in Dagster>                          # scheduled, retryable

They call the same `sync()`. That matters more than it looks: a scheduled job
that drifts from what a developer runs by hand is a job nobody trusts the
morning it goes red, and the usual cause is two implementations of "refresh the
catalogue" that were the same once.

## Why the projections come before the catalogue

The OpenMetadata payload is built *from* the graph and the ontology. Publishing
before regenerating them republishes the previous run's metrics under this run's
timestamp, which is the specific kind of wrong that looks right. `STAGES` is
ordered, and `sync()` walks it in order.

## Failure policy

A stage that fails does not stop the ones after it, and the run reports every
outcome. These are independent projections of the same build: a catalogue that
cannot be reached is no reason to leave the knowledge graph stale, and an agent
session an hour later needs that graph far more than it needs the catalogue.
The exit code is non-zero if anything failed, so a scheduler still sees red.

The one exception is ordering *within* the catalogue: tables are published after
the vocabulary, because a column's tag references a classification the
vocabulary pass creates.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

#: Bootstrap steps that regenerate a projection of the *data*, in dependency
#: order. Named rather than "every step", because `pf bootstrap` also scaffolds
#: files, rewrites CI workflows and merges settings — none of which a data run
#: makes stale, and all of which would turn a scheduled refresh into a scheduled
#: rewrite of the repository.
STAGES: tuple[str, ...] = (
    "knowledge graph",
    "context card",
    "MDL manifest",
    "OWL export",
    "otop manifest",
)


@dataclass
class StageResult:
    """One stage's outcome. `ok=False` is a finding, never an exception."""

    name: str
    ok: bool
    detail: str = ""
    seconds: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {"stage": self.name, "ok": self.ok, "detail": self.detail,
                "seconds": round(self.seconds, 2)}


@dataclass
class SyncResult:
    group: str
    project: str
    stages: list[StageResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(s.ok for s in self.stages)

    def as_dict(self) -> dict[str, Any]:
        return {
            "group": self.group, "project": self.project, "ok": self.ok,
            "stages": [s.as_dict() for s in self.stages],
            "failed": [s.name for s in self.stages if not s.ok],
        }


def _timed(name: str, fn) -> StageResult:  # noqa: ANN001 — any zero-arg callable
    start = time.monotonic()
    try:
        detail = fn() or ""
        return StageResult(name, True, str(detail)[:300], time.monotonic() - start)
    except Exception as exc:  # noqa: BLE001 — a broken stage is a result, see module docstring
        return StageResult(name, False, f"{type(exc).__name__}: {exc}"[:300],
                           time.monotonic() - start)


def sync(root: Path, group: str, project: str, *,
         stages: tuple[str, ...] = STAGES,
         catalogue: bool = True,
         tables: bool = True) -> SyncResult:
    """Refresh the projections, then publish to OpenMetadata.

    `catalogue=False` regenerates the local projections only, which is what a
    machine with no catalogue server wants — and what CI wants, where the graph
    matters and the catalogue is somebody else's deployment.
    """
    from pf.scaffold.bootstrap import STEPS

    result = SyncResult(group=group, project=project)
    by_name = {s.name: s for s in STEPS}

    for name in stages:
        step = by_name.get(name)
        if step is None:
            # A renamed bootstrap step should be loud. Silently skipping it
            # leaves a projection permanently stale with a green run.
            result.stages.append(StageResult(
                name, False, "no such bootstrap step — STAGES is out of date"))
            continue
        result.stages.append(_timed(name, lambda s=step: _run_step(s, root, group, project)))

    if catalogue:
        result.stages.append(_timed("catalogue vocabulary",
                                    lambda: _publish_vocabulary(root, group, project)))
        if tables:
            result.stages.append(_timed("catalogue tables",
                                        lambda: _publish_tables(root, group, project)))
    return result


def _run_step(step: Any, root: Path, group: str, project: str) -> str:
    """Run one bootstrap step and turn its result into a detail string."""
    out = step.run(root, group, project)
    rows = out if isinstance(out, list) else [out]
    bad = [r for r in rows if getattr(r, "status", "ok") == "failed"]
    if bad:
        raise RuntimeError("; ".join(f"{r.name}: {r.detail}" for r in bad))
    return "; ".join(str(getattr(r, "detail", "")) for r in rows if getattr(r, "detail", ""))


def _project_dir(root: Path, group: str, project: str) -> Path:
    return Path(root) / "groups" / group / "projects" / project


def _publish_vocabulary(root: Path, group: str, project: str) -> str:
    from pf.tools.openmetadata import publish_payload

    r = publish_payload(_project_dir(root, group, project), group, project, None)
    sent = ", ".join(f"{k}={v}" for k, v in r["sent"].items())
    if not r["ok"]:
        raise RuntimeError(f"{len(r['failed'])} failed — {r['failed'][0]}")
    return sent


def _publish_tables(root: Path, group: str, project: str) -> str:
    from pf.tools.openmetadata import publish_tables

    r = publish_tables(_project_dir(root, group, project), group, project, None)
    if not r["ok"]:
        raise RuntimeError(r.get("message") or
                           f"{len(r.get('failed', []))} failed — "
                           f"{(r.get('failed') or ['?'])[0]}")
    return (f"{r['tables']} table(s) in {r['schemas']} schema(s)"
            + (f", {r['skipped']} skipped (never built)" if r.get("skipped") else ""))


# --------------------------------------------------------------------- cli --
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="catalog_sync",
        description="Refresh graph, topology projections and the catalogue after a run.")
    parser.add_argument("group")
    parser.add_argument("project")
    parser.add_argument("--root", default=os.environ.get("PF_ROOT", ""),
                        help="repo root (default: discovered from cwd)")
    parser.add_argument("--no-catalogue", action="store_true",
                        help="regenerate local projections only, do not contact OpenMetadata")
    parser.add_argument("--no-tables", action="store_true",
                        help="publish the vocabulary but not the table entities")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    if args.root:
        root = Path(args.root)
    else:
        from pf import obs
        root = obs.repo_root()

    result = sync(root, args.group, args.project,
                  catalogue=not args.no_catalogue, tables=not args.no_tables)

    if args.json:
        print(json.dumps(result.as_dict(), indent=2))
    else:
        for s in result.stages:
            mark = "ok  " if s.ok else "FAIL"
            print(f"  {mark} {s.name:<22} {s.seconds:>6.2f}s  {s.detail}")
        print(f"  {'-' * 60}")
        print(f"  {args.group}/{args.project}: "
              f"{'all stages ok' if result.ok else 'FAILED: ' + ', '.join(result.as_dict()['failed'])}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
