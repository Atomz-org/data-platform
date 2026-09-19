"""Loop memory — what a project has already decided about its own findings.

A loop without memory re-discovers the same fact every run. The Monday-late
source gets paged every Monday; the mart that is deliberately unmetriced gets
proposed a metric every day; the test everyone agrees is too strict gets triaged
to the same root cause forever. Each of those is a correct finding the first
time and noise every time after, and noise is what makes an unattended loop
unsurvivable: the person who has to read STATE.md stops reading it.

So each project carries a small, hand-reviewable memory file, and every loop
consults it *before* a finding reaches the ledger:

    groups/<group>/projects/<project>/decisions/loop-memory.yaml

An entry is a pattern over finding text, the loop it applies to (or `*`), a
note saying *why*, who wrote it, and optionally when it expires. Two verbs:

  * **suppress** — drop the finding. For known, accepted conditions.
  * **annotate** — keep it, but append the note. For context a reader needs
    ("owner is on leave until …", "migration in flight").

## Why a file in `decisions/`, not a table

The memory is a decision, and decisions in this platform are reviewed in pull
requests. A suppression is precisely the kind of thing that should be visible
in a diff — it is the statement "we will stop looking at this" — and putting
it in the tracking DB would take it out of review. The file is YAML so the
comments survive, same reason as the ontology.

## Why expiry exists

A suppression that never expires is how a real incident hides behind an old
decision. `expires` is optional, but `pf loop memory audit` lists every entry
without one so the list stays a list someone reads.

## What memory must never do

It never widens what a loop may *write*. Memory filters findings; the gate
decides paths. A memory entry cannot name a file or loosen a budget, and the
loader rejects keys it does not know rather than carrying them along.
"""

from __future__ import annotations

import fnmatch
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import yaml

Verb = Literal["suppress", "annotate"]

MEMORY_REL = Path("decisions") / "loop-memory.yaml"

_ALLOWED_KEYS = frozenset({"id", "loop", "pattern", "verb", "note", "actor",
                           "created", "expires", "hits"})


class MemoryError(ValueError):
    """The memory file is malformed. Refused rather than partially applied."""


@dataclass
class Entry:
    id: str
    loop: str              # loop name, or "*"
    pattern: str           # glob (default) or /regex/ over the finding text
    verb: Verb
    note: str
    actor: str = ""
    created: str = ""
    expires: str = ""      # ISO date; empty means never
    hits: int = 0

    def matches(self, loop: str, finding: str) -> bool:
        if self.loop not in ("*", loop):
            return False
        if self.expired:
            return False
        pat = self.pattern
        if len(pat) > 2 and pat.startswith("/") and pat.endswith("/"):
            return re.search(pat[1:-1], finding) is not None
        return fnmatch.fnmatch(finding, pat) or pat.lower() in finding.lower()

    @property
    def expired(self) -> bool:
        if not self.expires:
            return False
        return self.expires[:10] < datetime.now(UTC).date().isoformat()

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return {k: v for k, v in d.items() if v not in ("", 0, None)} | {"id": self.id}


@dataclass
class Applied:
    """The result of running findings through memory."""

    kept: list[str] = field(default_factory=list)
    suppressed: list[tuple[str, Entry]] = field(default_factory=list)
    annotated: list[tuple[str, Entry]] = field(default_factory=list)

    @property
    def dropped(self) -> int:
        return len(self.suppressed)


def memory_path(project_dir: Path) -> Path:
    return project_dir / MEMORY_REL


def load(project_dir: Path) -> list[Entry]:
    p = memory_path(project_dir)
    if not p.exists():
        return []
    doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    rows = doc.get("entries") if isinstance(doc, dict) else doc
    if rows is None:
        return []
    if not isinstance(rows, list):
        raise MemoryError(f"{p}: `entries` must be a list")
    out: list[Entry] = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise MemoryError(f"{p}: entry {i} is not a mapping")
        unknown = set(row) - _ALLOWED_KEYS
        if unknown:
            raise MemoryError(f"{p}: entry {i} has unknown key(s) {sorted(unknown)} — "
                              f"memory filters findings and nothing else")
        verb = row.get("verb", "suppress")
        if verb not in ("suppress", "annotate"):
            raise MemoryError(f"{p}: entry {i}: verb must be suppress|annotate")
        if not row.get("pattern") or not row.get("note"):
            raise MemoryError(f"{p}: entry {i}: `pattern` and `note` are required — "
                              f"a suppression without a reason is a blind spot")
        out.append(Entry(
            id=str(row.get("id") or f"m{i}"), loop=str(row.get("loop", "*")),
            pattern=str(row["pattern"]), verb=verb, note=str(row["note"]),
            actor=str(row.get("actor", "")), created=str(row.get("created", "")),
            expires=str(row.get("expires", "")), hits=int(row.get("hits", 0) or 0)))
    return out


def save(project_dir: Path, entries: list[Entry]) -> Path:
    p = memory_path(project_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "# Loop memory — decisions this project has made about its own findings.\n"
        "# Reviewed in pull requests like any other decision. `pf loop memory` to\n"
        "# add, list and audit; a suppression without `expires` is listed by audit.\n"
    )
    body = yaml.safe_dump({"entries": [e.to_dict() for e in entries]},
                          sort_keys=False, allow_unicode=True)
    p.write_text(header + body, encoding="utf-8")
    return p


def remember(project_dir: Path, *, loop: str, pattern: str, note: str,
             verb: Verb = "suppress", actor: str = "", expires: str = "") -> Entry:
    entries = load(project_dir)
    e = Entry(id=str(uuid.uuid4())[:8], loop=loop or "*", pattern=pattern, verb=verb,
              note=note, actor=actor,
              created=datetime.now(UTC).date().isoformat(), expires=expires)
    entries.append(e)
    save(project_dir, entries)
    _decide(project_dir, "memory:remember", entry=e.id, loop=e.loop, verb=e.verb,
            pattern=e.pattern, note=e.note, actor=e.actor, expires=e.expires)
    return e


def forget(project_dir: Path, entry_id: str) -> bool:
    entries = load(project_dir)
    kept = [e for e in entries if e.id != entry_id]
    if len(kept) == len(entries):
        return False
    save(project_dir, kept)
    gone = next(e for e in entries if e.id == entry_id)
    _decide(project_dir, "memory:forget", entry=entry_id, pattern=gone.pattern,
            hits=gone.hits)
    return True


def _decide(project_dir: Path, name: str, **payload) -> None:
    from pf import obs, trace

    try:
        root = obs.repo_root(project_dir)
    except Exception:  # noqa: BLE001 — a bare tmp dir in tests has no repo root
        root = project_dir
    group = project = ""
    if project_dir.parent.name == "projects":
        group, project = project_dir.parent.parent.name, project_dir.name
    trace.decision(root, name, group=group, project=project, **payload)


def apply(project_dir: Path, loop: str, findings: list[str],
          *, count_hits: bool = True) -> Applied:
    """Run findings through memory. Suppressed ones never reach the ledger."""
    entries = load(project_dir)
    out = Applied()
    if not entries:
        out.kept = list(findings)
        return out
    touched = False
    for f in findings:
        hit = next((e for e in entries if e.matches(loop, f)), None)
        if hit is None:
            out.kept.append(f)
            continue
        hit.hits += 1
        touched = True
        if hit.verb == "suppress":
            out.suppressed.append((f, hit))
        else:
            out.annotated.append((f, hit))
            out.kept.append(f"{f} [memory {hit.id}: {hit.note}]")
    if touched and count_hits:
        save(project_dir, entries)
    return out


def audit(project_dir: Path) -> list[str]:
    """Entries a person should look at: expired, never-hit, or open-ended."""
    out: list[str] = []
    for e in load(project_dir):
        if e.expired:
            out.append(f"{e.id}: expired {e.expires} — delete or renew ({e.note})")
        elif e.verb == "suppress" and not e.expires:
            out.append(f"{e.id}: suppression with no expiry — `{e.pattern}` ({e.note})")
        elif e.hits == 0 and e.created and e.created < _days_ago(60):
            out.append(f"{e.id}: never matched in 60 days — `{e.pattern}`")
    return out


def _days_ago(n: int) -> str:
    from datetime import timedelta
    return (datetime.now(UTC) - timedelta(days=n)).date().isoformat()
