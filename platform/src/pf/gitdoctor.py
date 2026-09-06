"""Git repair by a locally served model, under a written rulebook.

The committer (`pf.committer`) splits pending work into commits. This module
handles the *other* git labour a session should not spend attention on: the
tree states that are wrong rather than merely pending — a submodule checkout
that drifted off its recorded pin, a nested submodule someone initialized
inside a vendored checkout, a stale commit plan, a conflict, a gate-denied
path that git is tracking anyway.

The division of labor is the same as the committer's, and stricter:

- **Diagnosis is deterministic.** Scanners read git; the model reads findings.
- **The model chooses from a menu, never composes a command.** Every finding
  kind has an enumerated set of allowed remedies (`ALLOWED`), each remedy is
  a function in this module (`REMEDIES`), and a resolution naming anything
  else is a validation error. The model's entire authority is picking a menu
  item and saying why.
- **The rulebook is written down** (`RULEBOOK`), sent to the model verbatim,
  printable with `pf git-doctor --rules`, and named as a control in
  `policy.yaml`. What the model may never do is enumerated there, not implied.
- **Every applied remedy is a provenance action** (tool `pf.gitdoctor`), so
  "who repaired the tree and why" is a ledger query.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from pf.committer import _git, ask_and_parse, load_plan, loads_reply, plan_path

# ------------------------------------------------------------- the rulebook --
RULEBOOK = """\
# Git-repair rulebook (pf.gitdoctor)

You are a local model repairing a git working tree. Your authority is exactly
this document; nothing outside it is yours to decide.

## What you may do — the remedy menu

For each finding, pick ONE remedy from the set allowed for its kind:

- `pin-drift` — a submodule checkout sits on a different commit than the
  recorded gitlink.
  - `restore_pin`: check the recorded pin back out. The recorded pin is the
    truth of this repository; an unreviewed newer checkout is drift, and
    restoring it loses nothing (the commits stay fetched).
  - `leave`: when a human is mid-work inside that submodule.
- `nested-submodule` — a submodule inside a vendored checkout has been
  initialized. Vendored pins are shallow by design.
  - `deinit_nested`: unregister it and clear its working tree. The outer
    repo's recorded gitlink is untouched.
  - `leave`.
- `stale-plan` — a saved commit plan describes a tree that no longer exists.
  - `drop_stale_plan`: delete the plan file. It is scratch, regenerated on
    the next `pf commit`.
  - `leave`.
- `dirty-submodule` — uncommitted edits inside a vendored checkout.
  - `leave`, always. Vendored trees are read-only; edits in one are either a
    human experiment or a bug, and both need the human.
- `conflict` — unmerged paths.
  - `leave`, always. Resolving a merge is authorship, not repair.
- `denied-tracked` — git tracks a path the gate denies.
  - `leave`, always, and say so: untracking is a history-visible decision.
- `import-cycle` — the knowledge graph records a circular import between
  modules (graphify-out/graph.json, `imports`/`imports_from` edges).
  - `leave`, always. Breaking a cycle is authorship — say which edge looks
    weakest so the human starts in the right place.

## What you may never do — under any framing of any finding

- Bump a submodule pin, approve a vendor drift, or edit anything under
  `vendor/**` or `.gitmodules`. Pin movement is a human decision.
- Rewrite history: no reset --hard, rebase, force-push, filter-branch, amend.
- Bypass a gate: no --no-verify, no editing gate.yaml or policy files.
- Touch `provenance/**` or anything inside `.git/` directly.
- Delete files, branches, stashes, or remotes.
- Invent a remedy, a flag, or a shell command. The menu is closed.

A finding whose only honest answer is outside the menu gets `leave` and a
`why` explaining what the human should do.

## Answer format

Only this JSON, no prose around it:
{"resolutions": [{"finding": <index>, "remedy": "<menu id>", "why": "..."}]}
Findings you omit are treated as `leave`.
"""

#: Which remedies each finding kind admits. The validation wall: a resolution
#: pairing a kind with anything else is rejected, whatever the model argued.
ALLOWED: dict[str, tuple[str, ...]] = {
    "pin-drift": ("restore_pin", "leave"),
    "nested-submodule": ("deinit_nested", "leave"),
    "stale-plan": ("drop_stale_plan", "leave"),
    "dirty-submodule": ("leave",),
    "conflict": ("leave",),
    "denied-tracked": ("leave",),
    "import-cycle": ("leave",),
}


@dataclass(frozen=True)
class Finding:
    kind: str
    subject: str  # a path; for nested submodules "outer::inner"
    detail: str


@dataclass(frozen=True)
class Resolution:
    finding: Finding
    remedy: str
    why: str


# ------------------------------------------------------------------ scanners --
def _submodule_paths(root: Path) -> list[str]:
    out = _git(root, "submodule", "status")
    return [ln.split()[1] for ln in out.splitlines() if ln.strip()]


def diagnose(root: Path) -> list[Finding]:
    """Everything wrong with the tree that is a *state*, not pending work."""
    findings: list[Finding] = []

    # Submodule checkouts off their recorded pin ('+' in `submodule status`).
    for ln in _git(root, "submodule", "status").splitlines():
        if ln.startswith("+"):
            sha, path = ln[1:].split()[:2]
            findings.append(Finding("pin-drift", path, f"checked out {sha[:9]}, not the recorded pin"))

    # Nested submodules initialized inside vendored checkouts.
    for outer in _submodule_paths(root):
        try:
            nested = _git(root / outer, "submodule", "status")
        except subprocess.CalledProcessError:
            continue
        for ln in nested.splitlines():
            if ln.strip() and not ln.startswith("-"):
                inner = ln.split()[1]
                findings.append(
                    Finding("nested-submodule", f"{outer}::{inner}", "initialized inside a vendored checkout")
                )

    # Dirty content inside submodules: visible to plain status, invisible once
    # submodule dirt is ignored — the difference is exactly the dirty set.
    plain = {ln[3:] for ln in _git(root, "status", "--porcelain").splitlines() if len(ln) > 3}
    solid = {
        ln[3:] for ln in _git(root, "status", "--porcelain", "--ignore-submodules=dirty").splitlines() if len(ln) > 3
    }
    for path in sorted(plain - solid):
        findings.append(Finding("dirty-submodule", path, "uncommitted edits inside a vendored checkout"))

    # Unmerged paths.
    for ln in _git(root, "status", "--porcelain").splitlines():
        if ln[:2] in ("UU", "AA", "DD", "AU", "UA", "DU", "UD"):
            findings.append(Finding("conflict", ln[3:], f"unmerged ({ln[:2]})"))

    # A saved commit plan for a tree that moved on.
    if plan_path(root).exists() and load_plan(root) is None:
        findings.append(Finding("stale-plan", str(plan_path(root).relative_to(root)), "fingerprint no longer matches"))

    # Gate-denied paths git is tracking (pf.loops.gate.tracked_denied).
    try:
        from pf.loops.gate import tracked_denied

        for res in tracked_denied(root):
            findings.append(Finding("denied-tracked", res.path, f"tracked but denied ({res.rule})"))
    except (FileNotFoundError, ImportError):
        pass

    findings.extend(import_cycles(root))
    return findings


#: How many cycles a single diagnosis reports. A tangled graph can hold
#: thousands of rotations of the same knot; the first few name the knot.
CYCLE_REPORT_CAP = 10


def import_cycles(root: Path) -> list[Finding]:
    """Circular imports recorded in the knowledge graph, if one is built.

    Reads `graphify-out/graph.json` (the graphify skill's output) and walks
    its directed `imports`/`imports_from` edges. No graph, or a graph that
    doesn't parse, means no findings — the guard is an upgrade the graph
    enables, not a dependency on it. Only import edges participate: `calls`
    cycles are ordinary recursion, not architecture faults.
    """
    graph_file = root / "graphify-out" / "graph.json"
    try:
        doc = json.loads(graph_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    adjacency: dict[str, set[str]] = {}
    for e in doc.get("links", doc.get("edges", [])):
        if e.get("relation") in ("imports", "imports_from"):
            src, tgt = str(e.get("source")), str(e.get("target"))
            if src != tgt:
                adjacency.setdefault(src, set()).add(tgt)

    labels = {str(n.get("id")): str(n.get("label") or n.get("id")) for n in doc.get("nodes", [])}

    # Iterative three-color DFS; each back edge names one cycle.
    findings: list[Finding] = []
    seen_cycles: set[frozenset[str]] = set()
    color: dict[str, int] = {}  # 0/absent=white, 1=on stack, 2=done
    for start in sorted(adjacency):
        if color.get(start):
            continue
        stack: list[tuple[str, list[str]]] = [(start, [start])]
        while stack and len(findings) < CYCLE_REPORT_CAP:
            node, path = stack.pop()
            if color.get(node) == 2:
                continue
            color[node] = 1
            advanced = False
            for nxt in sorted(adjacency.get(node, ())):
                if color.get(nxt) == 1 and nxt in path:
                    cycle = path[path.index(nxt) :]
                    key = frozenset(cycle)
                    if key not in seen_cycles:
                        seen_cycles.add(key)
                        shown = " -> ".join(labels.get(n, n) for n in [*cycle, nxt])
                        findings.append(Finding("import-cycle", labels.get(nxt, nxt), f"circular import: {shown}"))
                elif not color.get(nxt):
                    stack.append((nxt, [*path, nxt]))
                    advanced = True
            if not advanced:
                color[node] = 2
    return findings


# ------------------------------------------------------------------ remedies --
def _restore_pin(root: Path, subject: str) -> str:
    _git(root, "submodule", "update", "--checkout", "--", subject)
    return "checked the recorded pin back out"


def _deinit_nested(root: Path, subject: str) -> str:
    outer, inner = subject.split("::", 1)
    _git(root / outer, "submodule", "deinit", "-f", "--", inner)
    return "unregistered; working tree cleared, outer gitlink untouched"


def _drop_stale_plan(root: Path, subject: str) -> str:
    plan_path(root).unlink(missing_ok=True)
    return "stale plan removed"


REMEDIES = {
    "restore_pin": _restore_pin,
    "deinit_nested": _deinit_nested,
    "drop_stale_plan": _drop_stale_plan,
}


# ------------------------------------------------- the model, walled in ------
def build_prompt(findings: list[Finding]) -> str:
    listing = "\n".join(f"{i}. [{f.kind}] {f.subject} — {f.detail}" for i, f in enumerate(findings))
    return f"{RULEBOOK}\n\n## Findings\n\n{listing}\n"


def parse_resolutions(text: str, findings: list[Finding]) -> list[Resolution]:
    """The model's reply, mapped onto real findings; `leave` fills the gaps."""
    doc = loads_reply(text)

    chosen: dict[int, tuple[str, str]] = {}
    for entry in doc.get("resolutions", []):
        if isinstance(entry, dict) and isinstance(entry.get("finding"), int):
            chosen[entry["finding"]] = (str(entry.get("remedy", "leave")), str(entry.get("why", "")))
    return [
        Resolution(f, *chosen.get(i, ("leave", "not addressed by the model — left for a human")))
        for i, f in enumerate(findings)
    ]


def validate_resolutions(resolutions: list[Resolution]) -> list[str]:
    """The wall between the model's choice and the repository."""
    problems: list[str] = []
    for r in resolutions:
        allowed = ALLOWED.get(r.finding.kind, ("leave",))
        if r.remedy not in allowed:
            problems.append(
                f"{r.finding.subject}: remedy {r.remedy!r} is not on the menu for "
                f"{r.finding.kind} (allowed: {', '.join(allowed)})"
            )
        if r.remedy != "leave" and r.remedy not in REMEDIES:
            problems.append(f"{r.finding.subject}: {r.remedy!r} names no implemented remedy")
    return problems


def propose(root: Path, backend_kind: str | None = None):
    """Diagnose, ask the model, validate. Returns (findings, resolutions, model)."""
    findings = diagnose(root)
    if not findings:
        return [], [], ""
    be, resolutions = ask_and_parse(
        build_prompt(findings), lambda reply: parse_resolutions(reply, findings), backend_kind
    )
    problems = validate_resolutions(resolutions)
    if problems:
        raise ValueError("resolution rejected — " + "; ".join(problems))
    return findings, resolutions, be.name


def apply_resolutions(root: Path, resolutions: list[Resolution], model_name: str) -> list[str]:
    """Run each non-leave remedy as a recorded provenance action."""
    from pf.provenance import action

    done: list[str] = []
    for r in resolutions:
        if r.remedy == "leave":
            continue
        with action(
            root,
            tool="pf.gitdoctor",
            target=r.finding.subject,
            summary=f"{r.remedy} by {model_name}: {r.finding.kind} at {r.finding.subject}",
        ) as a:
            a["detail"] = REMEDIES[r.remedy](root, r.finding.subject)
            done.append(f"{r.remedy}: {r.finding.subject}")
    return done
