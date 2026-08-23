"""Closing the loop: finding -> patch -> branch -> impact -> review -> PR.

Every loop in the registry used to stop at *reporting*. That is the right place
to stop on day one, and the wrong place to stop forever: a triage that names the
fix and then waits for a person to type it is a report, not an agent. This
module is the other half — the sequence a loop runs once it has earned L2.

    Proposal  (files, title, rationale — produced by the loop body)
      -> gate        every path through `check_paths`; one deny stops the run
      -> worktree    a fresh `git worktree` on a new branch; the operator's
                     checkout is never touched
      -> commit      the proposal's files, one commit, attributed to the loop
      -> impact      `pf.pr.build` on the branch: blast radius, gate verdicts
      -> review      Recce, if installed and a baseline exists; otherwise noted
      -> pr          `gh pr create` if `gh` and a remote exist; else the branch
                     is left for a person, and the proposal says so
      -> record      data/proposals/<id>.json — what the control plane reads

The verdict a proposal can reach is `proposed`, never `merged`. Merging is what
L3 would mean, and nothing is L3. When something is, the merge step goes here
and nowhere else — behind the same gate, from the same evidence.

## What the level changes

  L1   the proposal is *recorded* and nothing else. No branch, no PR. This is
       how an L1 loop shows what it would have done — the promotion evidence.
  L2   everything above, ending in a PR that a human reviews.
  L3   identical to L2 today. The merge step is intentionally absent.

## Why a worktree and not the working tree

A loop runs on a schedule, which means it runs while someone is mid-edit. Writing
into their checkout would mix the loop's change with theirs; stashing would move
their work somewhere they did not put it. A worktree costs a directory and
touches nothing the person can see.

## Why impact runs even when the loop already ran it

The loop body reasons over the graph to *decide* the fix. The impact report here
is computed from the branch's actual diff, after the write, and is attached to
the PR as the reviewer's evidence. If the two disagree, the second one is right,
and that disagreement is worth a reviewer's attention.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pf import trace
from pf.loops.gate import check_paths

Status = Literal["recorded", "gate_blocked", "branched", "proposed", "error"]

PROPOSALS_REL = Path("data") / "proposals"


@dataclass
class Proposal:
    """What a loop wants to change. Produced by the body; executed here.

    `files` are project-relative paths to full new contents. Whole files, not
    patches: a loop that emits a diff against what it *thinks* the file says
    writes garbage the day the file moved, and whole-file writes fail loudly
    on a conflict instead.
    """

    loop: str
    title: str
    rationale: str
    files: dict[str, str]
    finding: str = ""
    confidence: str = "medium"
    labels: tuple[str, ...] = ("loop",)
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["labels"] = list(self.labels)
        return d


@dataclass
class Outcome:
    proposal_id: str
    status: Status
    level: str
    branch: str = ""
    commit: str = ""
    pr_url: str = ""
    impact_severity: str = ""
    impact_total: int = 0
    gate: list[dict[str, str]] = field(default_factory=list)
    review: str = ""
    message: str = ""
    recorded_at: str = ""
    path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ------------------------------------------------------------------- git ----
def _git(cwd: Path, *args: str, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True,
                          text=True, check=check)


def _has_remote(root: Path) -> bool:
    return bool(_git(root, "remote").stdout.strip())


def _gh_available() -> bool:
    return shutil.which("gh") is not None


def branch_name(p: Proposal) -> str:
    return f"loop/{p.loop}/{p.id}"


def proposals_dir(root: Path) -> Path:
    return root / PROPOSALS_REL


def _record(root: Path, p: Proposal, out: Outcome) -> Path:
    d = proposals_dir(root)
    d.mkdir(parents=True, exist_ok=True)
    out.recorded_at = datetime.now(UTC).isoformat(timespec="seconds")
    path = d / f"{p.id}.json"
    out.path = str(path.relative_to(root)).replace("\\", "/")
    path.write_text(json.dumps({"proposal": p.to_dict(), "outcome": out.to_dict()},
                               indent=2), encoding="utf-8")
    trace.get().step("record", status=out.status, path=out.path, message=out.message)
    return path


def load_all(root: Path) -> list[dict[str, Any]]:
    d = proposals_dir(root)
    if not d.exists():
        return []
    rows = []
    for f in sorted(d.glob("*.json")):
        try:
            rows.append(json.loads(f.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return rows


def mark(root: Path, proposal_id: str, status: str, *, actor: str, note: str = "") -> bool:
    """A human closed the loop: accepted, rejected or reverted. Kept on the record."""
    path = proposals_dir(root) / f"{proposal_id}.json"
    if not path.exists():
        return False
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc.setdefault("resolution", {})
    doc["resolution"] = {"status": status, "actor": actor, "note": note,
                         "at": datetime.now(UTC).isoformat(timespec="seconds")}
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    trace.decision(root, f"proposal:{status}", proposal=proposal_id,
                   loop=doc.get("proposal", {}).get("loop", ""),
                   title=doc.get("proposal", {}).get("title", ""),
                   actor=actor, note=note)
    return True


# --------------------------------------------------------------- execute ----
def execute(root: Path, group: str, project: str, p: Proposal, *,
            level: str, dry_run: bool = False,
            open_pr: bool = True, run_review: bool = True) -> Outcome:
    """Run the chain as far as the level allows. Never merges."""
    out = Outcome(proposal_id=p.id, status="recorded", level=level)
    tr = trace.get()
    tr.step("proposal", proposal=p.id, loop=p.loop, title=p.title, files=list(p.files),
            level=level, confidence=p.confidence)

    if not p.files:
        out.message = "proposal carries no files"
        _record(root, p, out)
        return out

    # The gate first, at every level: an L1 proposal that *would* be blocked is
    # worth knowing about before the loop is promoted, not after.
    rel_paths = [str(Path("groups") / group / "projects" / project / f).replace("\\", "/")
                 for f in p.files]
    results = check_paths(rel_paths, root, in_project=True)
    out.gate = [{"path": r.path, "verdict": r.verdict, "rule": r.rule} for r in results]
    tr.step("gate", "blocked" if any(r.blocked for r in results) else "passed",
            verdicts=out.gate)
    if any(r.blocked for r in results):
        out.status = "gate_blocked"
        out.message = "; ".join(f"{r.path}: {r.rule}" for r in results if r.blocked)
        _record(root, p, out)
        return out

    if level == "L1" or dry_run:
        out.message = ("dry run: recorded only" if dry_run
                       else "L1: recorded only — promote the loop to let it branch")
        _record(root, p, out)
        return out

    branch = branch_name(p)
    wt = root / ".worktrees" / p.id
    try:
        wt.parent.mkdir(exist_ok=True)
        r = _git(root, "worktree", "add", "-b", branch, str(wt), "HEAD")
        if r.returncode != 0:
            raise RuntimeError(f"worktree: {r.stderr.strip()[:300]}")
        out.branch = branch

        for rel, content in p.files.items():
            target = wt / "groups" / group / "projects" / project / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            _git(wt, "add", str(target.relative_to(wt)))

        msg = f"{p.title}\n\n{p.rationale}\n\nLoop: {p.loop} · proposal {p.id}"
        env = {**os.environ,
               "GIT_AUTHOR_NAME": f"pf loop {p.loop}", "GIT_AUTHOR_EMAIL": "loops@pf.local",
               "GIT_COMMITTER_NAME": f"pf loop {p.loop}", "GIT_COMMITTER_EMAIL": "loops@pf.local"}
        r = subprocess.run(["git", "commit", "-q", "-m", msg], cwd=str(wt),
                           capture_output=True, text=True, env=env)
        if r.returncode != 0:
            raise RuntimeError(f"commit: {r.stderr.strip()[:300] or r.stdout.strip()[:300]}")
        out.commit = _git(wt, "rev-parse", "--short", "HEAD").stdout.strip()
        out.status = "branched"
        tr.step("branch", branch=branch, commit=out.commit, worktree=str(wt))

        # Impact from the branch's real diff.
        try:
            from pf import pr as pr_mod
            report = pr_mod.build(wt, base="HEAD~1", title=p.title)
            order = ("safe", "review", "breaking")
            sev = [s.severity for s in report.projects if s.severity in order] or ["safe"]
            out.impact_severity = max(sev, key=order.index)
            out.impact_total = sum(s.impacted for s in report.projects)
            body_md = pr_mod.markdown(report)
        except Exception as exc:  # noqa: BLE001 — impact is evidence, not a gate here
            body_md = f"_impact report unavailable: {type(exc).__name__}: {exc}_"
            out.review = f"impact failed: {exc}"[:200]
        tr.step("impact", severity=out.impact_severity or "n/a", total=out.impact_total)

        if run_review:
            out.review = (out.review + "; " if out.review else "") + _review(wt, group, project)
            tr.step("review", detail=out.review)

        if open_pr and _gh_available() and _has_remote(root):
            push = _git(wt, "push", "-u", "origin", branch)
            if push.returncode != 0:
                out.message = f"push failed: {push.stderr.strip()[:200]}"
            else:
                body = (f"{p.rationale}\n\n**Finding:** {p.finding}\n\n"
                        f"**Confidence:** {p.confidence}\n\n---\n\n{body_md}\n\n"
                        f"_Opened by `pf loop {p.loop}` at {level}. A human merges; "
                        f"a loop never does._")
                r = subprocess.run(
                    ["gh", "pr", "create", "--title", p.title, "--body", body,
                     "--head", branch, *[a for lb in p.labels for a in ("--label", lb)]],
                    cwd=str(wt), capture_output=True, text=True)
                if r.returncode == 0:
                    out.pr_url = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
                    out.status = "proposed"
                else:
                    out.message = f"gh pr create failed: {r.stderr.strip()[:200]}"
        else:
            out.message = (f"branch `{branch}` left for review: "
                           + ("no `gh`" if not _gh_available() else "no remote"))
        tr.step("pr", out.status, url=out.pr_url, message=out.message)
    except Exception as exc:  # noqa: BLE001 — a loop must never take the platform down
        out.status = "error"
        out.message = f"{type(exc).__name__}: {exc}"[:400]
        tr.error(exc, step="chain")
    finally:
        if wt.exists():
            _git(root, "worktree", "remove", "--force", str(wt))
    _record(root, p, out)
    return out


def _review(wt: Path, group: str, project: str) -> str:
    """Recce, when it is there. Its absence is a fact, not a failure."""
    try:
        from pf.tools import get
        tool = get("recce")
    except Exception:  # noqa: BLE001
        return "recce not registered"
    if tool.missing():
        return "recce not installed"
    try:
        from pf.tools import recce as rc
        pdir = wt / "groups" / group / "projects" / project
        if not rc.has_baseline(pdir):
            return "recce: no baseline — `pf recce baseline` first"
        res = rc.run(pdir, skip_query=True)
        if res.get("ok"):
            return "recce: checks passed"
        return f"recce: {res.get('reason') or 'failed'} — {res.get('message', '')}"[:200]
    except Exception as exc:  # noqa: BLE001
        return f"recce failed: {type(exc).__name__}: {exc}"[:200]
