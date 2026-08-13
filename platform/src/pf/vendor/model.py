"""Track what each vendored upstream contributed, and notice when it moves.

The problem this solves is narrow and real. A README that says "ported from
dbt-agent-skills" is true on the day it is written and unfalsifiable afterwards:
upstream renames a skill, our port keeps working, and the provenance quietly
becomes fiction. Nothing checks, because there is nothing to check against.

Here the claim is a path pair — one file upstream, one or more of ours — and both
ends are verifiable:

    pf vendor verify   every declared upstream path still exists, and every
                       schema contract still holds
    pf vendor sync     fetch each upstream's tracking branch, then report which
                       *adopted* paths changed and which of our files they touch
    pf vendor why      reverse lookup: where did this file of ours come from

DIGESTS ARE GIT'S, NOT OURS. The identity of a path at a commit is
`git rev-parse <commit>:<path>` — the blob OID for a file, the tree OID for a
directory. It is exact, it costs one process, and it is the same notion of
"changed" that the upstream project itself uses. Hashing file contents ourselves
would reimplement that badly and disagree on renames.

WHY THE LOCK FILE IS SEPARATE FROM THE SUBMODULE POINTER. The gitlink already
records which commit we are on. What it cannot record is which commit we last
*reviewed* — those differ the moment someone runs `git submodule update --remote`
without reading anything. The lock stores the reviewed state, so drift is
measured against human attention rather than against a checkout.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

REGISTRY = Path(__file__).parent / "registry.yaml"
LOCK_NAME = "vendor.lock.json"

Kind = Literal["shape", "port", "parity", "schema", "data"]

# How loudly an upstream change should land. A schema break can fail a build; a
# `shape` note is a reading suggestion. Ranking them stops every sync turning
# into an undifferentiated wall of "something moved".
SEVERITY: dict[str, str] = {
    "schema": "error",
    "data": "error",
    "parity": "warning",
    "port": "warning",
    "shape": "info",
}


@dataclass(frozen=True)
class Adoption:
    upstream: str
    kind: Kind
    ours: list[str] = field(default_factory=list)
    note: str = ""

    @property
    def severity(self) -> str:
        return SEVERITY.get(self.kind, "info")


@dataclass(frozen=True)
class Declined:
    what: str
    why: str


@dataclass(frozen=True)
class Upstream:
    id: str
    name: str
    url: str
    path: str
    branch: str
    licence: str
    role: str
    why: str = ""
    licence_review: str = ""
    adopted: list[Adoption] = field(default_factory=list)
    declined: list[Declined] = field(default_factory=list)

    @property
    def needs_licence_review(self) -> bool:
        return bool(self.licence_review)

    def our_files(self) -> set[str]:
        return {o for a in self.adopted for o in a.ours}


def load_registry(path: Path | None = None) -> list[Upstream]:
    doc = yaml.safe_load((path or REGISTRY).read_text()) or {}
    out: list[Upstream] = []
    for u in doc.get("upstreams") or []:
        out.append(Upstream(
            id=u["id"], name=u["name"], url=u["url"], path=u["path"],
            branch=u.get("branch", "main"), licence=u.get("licence", "unknown"),
            role=u.get("role", "reference"), why=(u.get("why") or "").strip(),
            licence_review=(u.get("licence_review") or "").strip(),
            adopted=[Adoption(upstream=a["upstream"], kind=a.get("kind", "shape"),
                              ours=list(a.get("ours") or []),
                              note=(a.get("note") or "").strip())
                     for a in (u.get("adopted") or [])],
            declined=[Declined(what=d["what"], why=(d.get("why") or "").strip())
                      for d in (u.get("declined") or [])],
        ))
    return out


# ------------------------------------------------------------------- git ----
def _git(cwd: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or f"git {' '.join(args)} failed")
    return r.stdout.strip()


def head(root: Path, u: Upstream) -> str:
    """Commit the submodule is checked out at, or "" if it was never initialised."""
    d = root / u.path
    if not (d / ".git").exists():
        return ""
    try:
        return _git(d, "rev-parse", "HEAD")
    except RuntimeError:
        return ""


def oid(root: Path, u: Upstream, rel: str, commit: str = "HEAD") -> str:
    """Git's identity for a path at a commit: blob OID for a file, tree for a dir.

    Returns "" when the path does not exist there — which is itself the finding
    we care about most, because an upstream rename silently orphans a port.
    """
    try:
        return _git(root / u.path, "rev-parse", f"{commit}:{rel}")
    except RuntimeError:
        return ""


# ------------------------------------------------------------------ lock ----
def lock_path(root: Path) -> Path:
    return Path(root) / LOCK_NAME


def read_lock(root: Path) -> dict[str, Any]:
    p = lock_path(root)
    return json.loads(p.read_text()) if p.exists() else {"version": 1, "upstreams": {}}


def write_lock(root: Path, data: dict[str, Any]) -> Path:
    p = lock_path(root)
    p.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    return p


def snapshot(root: Path, ups: list[Upstream] | None = None) -> dict[str, Any]:
    """The reviewed state: each upstream's commit plus an OID per adopted path."""
    ups = ups if ups is not None else load_registry()
    out: dict[str, Any] = {"version": 1, "upstreams": {}}
    for u in ups:
        c = head(root, u)
        if not c:
            continue
        out["upstreams"][u.id] = {
            "commit": c,
            "branch": u.branch,
            "adopted": {a.upstream: oid(root, u, a.upstream, c) for a in u.adopted},
        }
    return out


# ----------------------------------------------------------------- drift ----
@dataclass
class PathDrift:
    upstream_id: str
    path: str
    kind: str
    severity: str
    state: Literal["changed", "removed", "added"]
    ours: list[str]
    note: str = ""

    def __str__(self) -> str:
        verb = {"changed": "changed upstream", "removed": "NO LONGER EXISTS upstream",
                "added": "newly tracked"}[self.state]
        return f"[{self.severity}] {self.upstream_id}: {self.path} {verb}"


@dataclass
class RepoDrift:
    upstream_id: str
    name: str
    locked: str
    current: str
    commits_behind: int
    paths: list[PathDrift] = field(default_factory=list)

    @property
    def moved(self) -> bool:
        return bool(self.locked) and self.locked != self.current

    @property
    def needs_review(self) -> bool:
        """A moved upstream that touched nothing we adopted is a free fast-forward."""
        return bool(self.paths)

    @property
    def severity(self) -> str:
        for level in ("error", "warning", "info"):
            if any(p.severity == level for p in self.paths):
                return level
        return "none"

    def affected_files(self) -> list[str]:
        seen: list[str] = []
        for p in self.paths:
            for o in p.ours:
                if o not in seen:
                    seen.append(o)
        return seen


def drift(root: Path, ups: list[Upstream] | None = None) -> list[RepoDrift]:
    """Compare the checkout against the lock. Local only — never fetches.

    Read this as "what moved since a human last looked", not "what is new
    upstream". `sync(fetch=True)` is what goes to the network.
    """
    ups = ups if ups is not None else load_registry()
    lock = read_lock(root)
    out: list[RepoDrift] = []
    for u in ups:
        cur = head(root, u)
        rec = (lock.get("upstreams") or {}).get(u.id) or {}
        locked = rec.get("commit", "")
        d = RepoDrift(upstream_id=u.id, name=u.name, locked=locked, current=cur,
                      commits_behind=_behind(root, u, locked, cur))
        if not cur:
            out.append(d)
            continue
        prev_oids: dict[str, str] = rec.get("adopted") or {}
        for a in u.adopted:
            now = oid(root, u, a.upstream, cur)
            was = prev_oids.get(a.upstream)
            if was is None:
                # Newly declared by us, or never locked. Not upstream movement.
                if locked:
                    d.paths.append(PathDrift(u.id, a.upstream, a.kind, "info",
                                             "added", a.ours, a.note))
                continue
            if not now:
                d.paths.append(PathDrift(u.id, a.upstream, a.kind, "error",
                                         "removed", a.ours, a.note))
            elif now != was:
                d.paths.append(PathDrift(u.id, a.upstream, a.kind, a.severity,
                                         "changed", a.ours, a.note))
        out.append(d)
    return out


def _behind(root: Path, u: Upstream, locked: str, current: str) -> int:
    if not locked or not current or locked == current:
        return 0
    try:
        n = _git(root / u.path, "rev-list", "--count", f"{locked}..{current}")
        return int(n)
    except (RuntimeError, ValueError):
        return -1  # shallow clone cannot count; the OID comparison still holds


# ------------------------------------------------------------------ sync ----
def sync(root: Path, ups: list[Upstream] | None = None,
         only: str = "") -> tuple[list[RepoDrift], list[str]]:
    """Fetch each tracking branch, then report drift. Does NOT write the lock.

    Separating the fetch from the lock write is the whole safety property: after
    a sync the working tree is ahead of the reviewed state, and it stays that way
    until someone runs `pf vendor approve`. A sync that silently updated the lock
    would make drift permanently unobservable.
    """
    ups = [u for u in (ups if ups is not None else load_registry())
           if not only or u.id == only]
    errors: list[str] = []
    for u in ups:
        try:
            _git(root, "submodule", "update", "--remote", "--recursive", "--", u.path)
        except RuntimeError as exc:
            errors.append(f"{u.id}: {exc}")
    return drift(root, ups), errors


def approve(root: Path, ids: list[str] | None = None) -> tuple[Path, list[str]]:
    """Record the current checkout as reviewed, for all upstreams or some."""
    ups = load_registry()
    fresh = snapshot(root, ups)
    if ids:
        lock = read_lock(root)
        for i in ids:
            if i in fresh["upstreams"]:
                lock.setdefault("upstreams", {})[i] = fresh["upstreams"][i]
        return write_lock(root, lock), ids
    return write_lock(root, fresh), sorted(fresh["upstreams"])


# ------------------------------------------------------------------- why ----
def why(root: Path, our_path: str) -> list[tuple[Upstream, Adoption]]:
    """Which upstream(s) a file of ours descends from.

    Matches on prefix so `pf vendor why platform/src/pf/projections/mdl.py`
    answers, and so does a directory.
    """
    q = our_path.strip().lstrip("./")
    out = []
    for u in load_registry():
        for a in u.adopted:
            for o in a.ours:
                if o == q or q.startswith(o.rstrip("/") + "/") or o.startswith(q.rstrip("/") + "/"):
                    out.append((u, a))
                    break
    return out
