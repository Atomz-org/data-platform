"""The onboarding funnel — the ladder as a product, with one number on the front.

Point the platform at an existing dbt repository and it climbs:

    import -> ontology -> dialect -> layers -> metrics -> review

Each rung already has a deterministic evaluate and validate (`ladder.py`). This
module adds the two things a *front door* needs and a ladder does not:

  * **`ship`** — when a stage validates, its working-tree changes become one
    pull request through the same chain a loop proposal takes
    (`pf.loops.actions`): gate, branch, impact, Recce, PR. One PR per stage,
    scoped to the files the stage owns, with the validation evidence in the
    body. A reviewer sees "ontology stage: 14 files, 0 breaking" instead of a
    1,200-file import.
  * **`funnel`** — time-to-first-governed-metric, read from the ledger. The
    ladder records every validation as a loop run; the funnel is the elapsed
    time from the first `onboard-import` row to the first `onboard-metrics`
    row that passed. That is the number the homepage shows and the number a
    buyer asks for, so it comes from the ledger rather than from a claim.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from pf.loops.runner import Ledger

STAGE_ORDER = ("import", "ontology", "dialect", "layers", "metrics", "review")


# ----------------------------------------------------------------- funnel ---
@dataclass
class StageTiming:
    stage: str
    first_attempt: str = ""
    first_pass: str = ""
    attempts: int = 0

    @property
    def passed(self) -> bool:
        return bool(self.first_pass)


@dataclass
class Funnel:
    group: str
    project: str
    stages: list[StageTiming] = field(default_factory=list)

    @property
    def started(self) -> str:
        return next((s.first_attempt for s in self.stages if s.first_attempt), "")

    def _stage(self, name: str) -> StageTiming | None:
        return next((s for s in self.stages if s.stage == name), None)

    @property
    def first_governed_metric(self) -> str:
        s = self._stage("metrics")
        return s.first_pass if s else ""

    @property
    def hours_to_first_governed_metric(self) -> float | None:
        if not self.started or not self.first_governed_metric:
            return None
        return round(_hours(self.started, self.first_governed_metric), 1)

    @property
    def current(self) -> str:
        for s in self.stages:
            if not s.passed:
                return s.stage
        return "done"

    def to_dict(self) -> dict[str, Any]:
        return {"group": self.group, "project": self.project, "started": self.started,
                "current": self.current,
                "hours_to_first_governed_metric": self.hours_to_first_governed_metric,
                "stages": [s.__dict__ for s in self.stages]}


def _hours(a: str, b: str) -> float:
    ta, tb = datetime.fromisoformat(a), datetime.fromisoformat(b)
    return (tb - ta).total_seconds() / 3600


def funnel(root: Path, group: str, project: str) -> Funnel:
    rows = [e for e in Ledger(root).read()
            if e.get("project") == project and str(e.get("loop", "")).startswith("onboard-")]
    f = Funnel(group, project)
    for stage in STAGE_ORDER:
        t = StageTiming(stage)
        for e in rows:
            if e["loop"] != f"onboard-{stage}":
                continue
            t.attempts += 1
            t.first_attempt = t.first_attempt or e["started_at"]
            if e["outcome"] in ("ok", "noop") and not t.first_pass:
                t.first_pass = e["started_at"]
        f.stages.append(t)
    return f


def funnel_all(root: Path, projects: list[tuple[str, str]]) -> list[Funnel]:
    return [funnel(root, g, p) for g, p in projects]


# ------------------------------------------------------------------ ship ---
def ship_stage(root: Path, group: str, project: str, stage: Any, verdict: Any, *,
               dry_run: bool = False) -> Any:
    """One PR for one stage's working-tree changes, via the proposal chain.

    The stage's `owns` globs bound what is shipped: a file the stage does not
    own is left in the working tree and named in the outcome, because shipping
    it would be the drive-by refactor the verifier exists to catch.
    """
    from pf.loops.actions import Proposal, execute
    from pf.onboard.ladder import _owned, changed

    pdir = root / "groups" / group / "projects" / project
    prefix = str(pdir.relative_to(root)).replace("\\", "/") + "/"
    files: dict[str, str] = {}
    skipped: list[str] = []
    for status, path in changed(root, pdir):
        rel = path.replace("\\", "/").removeprefix(prefix)
        if status == "D":
            skipped.append(f"{rel} (deleted — delete by hand in the PR)")
            continue
        if stage.owns and not _owned(rel, stage.owns):
            skipped.append(rel)
            continue
        f = root / path
        if not f.is_file():
            continue
        try:
            files[rel] = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            skipped.append(f"{rel} (binary)")
    evidence = "\n".join(f"- {c.status}: {c.name} — {c.evidence}" for c in verdict.checks)
    p = Proposal(
        loop=f"onboard-{stage.name}",
        title=f"onboard({project}): {stage.title}",
        rationale=(f"Stage **{stage.name}** of the onboarding ladder for `{group}/{project}`.\n\n"
                   f"{stage.subject}\n\n### Validation\n{evidence}\n"
                   + (f"\n_Not shipped (outside the stage's scope): "
                      f"{', '.join(skipped[:12])}_" if skipped else "")),
        files=files,
        finding=verdict.summary,
        confidence="high" if verdict.complete else "medium",
        labels=("onboarding", stage.name),
    )
    out = execute(root, group, project, p, level="L2", dry_run=dry_run)
    out.review = (out.review + "; " if out.review else "") + \
        (f"{len(skipped)} file(s) outside scope left in tree" if skipped else "scope clean")
    return out
