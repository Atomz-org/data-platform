"""Turn the provenance registry into checks that can actually fail.

Three questions, in increasing order of how much they are worth:

  1. Does every declared upstream path still exist?  An upstream rename orphans
     a port silently — our code keeps working, and the provenance becomes a
     story. This is the cheapest check here and the one that catches the most.
  2. Does every file of ours named in the registry still exist?  Provenance that
     points at a deleted file is worse than none: it makes a stale registry look
     maintained.
  3. Do the contract adoptions still hold?  `schema` means an artefact of ours
     validates against a vendored schema file; `parity` means upstream's required
     fields all have a counterpart in ours.

The third is why the submodules exist at all. Before they were pinned, "our MDL
follows Wren's schema" was a sentence in a docstring — and it was wrong once
(`layoutVersion` as a string, where the schema says integer). A vendored schema
turns that class of mistake into a test failure.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pf.vendor.model import Upstream, load_registry, oid

Severity = str  # "error" | "warning" | "info"


@dataclass
class Finding:
    severity: Severity
    check: str
    subject: str
    message: str

    def __str__(self) -> str:
        return f"[{self.severity}] {self.check}: {self.subject} — {self.message}"


@dataclass
class Result:
    findings: list[Finding]
    checked: int

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "error"]

    @property
    def ok(self) -> bool:
        return not self.errors


# ------------------------------------------------------------- existence ----
def check_paths(root: Path, ups: list[Upstream]) -> list[Finding]:
    out: list[Finding] = []
    for u in ups:
        sub = root / u.path
        if not (sub / ".git").exists():
            out.append(Finding("error", "submodule", u.id,
                               f"not initialised — run `git submodule update --init {u.path}`"))
            continue
        for a in u.adopted:
            if not oid(root, u, a.upstream):
                out.append(Finding(
                    "error", "upstream-path", f"{u.id}:{a.upstream}",
                    "no longer exists upstream; the provenance for "
                    + ", ".join(a.ours) + " is stale"))
            for o in a.ours:
                if not (root / o).exists():
                    out.append(Finding("error", "our-path", o,
                                       f"declared as derived from {u.id} but missing"))
    return out


# -------------------------------------------------------------- contracts ----
def _validator(schema_path: Path):
    import jsonschema

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    cls = jsonschema.validators.validator_for(schema)
    cls.check_schema(schema)
    return cls(schema)


def check_otop(root: Path, project_dir: Path | None = None) -> list[Finding]:
    """Our policy export against `vendor/opentopology/schemas/otop-core-v0.2.schema.json`."""
    schema = root / "vendor" / "opentopology" / "schemas" / "otop-core-v0.2.schema.json"
    if not schema.exists():
        return [Finding("error", "contract:otop", str(schema), "vendored schema missing")]
    from pf.projections.otop import build_manifest

    m = build_manifest(root, project_dir=project_dir)
    errs = sorted(_validator(schema).iter_errors(m), key=lambda e: list(e.path))
    if not errs:
        return [Finding("info", "contract:otop", "otop-core 0.2",
                        f"{len(m['objects'])} objects, "
                        f"{len(m['relationships'])} relationships conform")]
    return [Finding("error", "contract:otop", "/" + "/".join(str(p) for p in e.path),
                    e.message[:200]) for e in errs[:10]]


def check_mdl(root: Path, project_dir: Path, group: str, project: str) -> list[Finding]:
    """Our MDL manifest against `vendor/wrenai/core/wren-mdl/mdl.schema.json`."""
    schema = root / "vendor" / "wrenai" / "core" / "wren-mdl" / "mdl.schema.json"
    if not schema.exists():
        return [Finding("error", "contract:mdl", str(schema), "vendored schema missing")]
    from pf.projections.mdl import build_manifest

    try:
        m = build_manifest(project_dir, group, project)
    except Exception as exc:  # noqa: BLE001 — no graph yet is not a schema failure
        return [Finding("warning", "contract:mdl", f"{group}/{project}",
                        f"could not build: {type(exc).__name__}: {exc}"[:160])]
    errs = sorted(_validator(schema).iter_errors(m), key=lambda e: list(e.path))
    if not errs:
        return [Finding("info", "contract:mdl", f"{group}/{project}",
                        f"{len(m['models'])} models, "
                        f"{len(m['relationships'])} relationships conform")]
    return [Finding("error", "contract:mdl",
                    f"{group}/{project} /" + "/".join(str(p) for p in e.path),
                    e.message[:200]) for e in errs[:10]]


# Which LoopSpec attribute (or platform artefact) answers each field upstream's
# pattern schema marks required. Recorded here rather than inferred, so a new
# required field upstream shows up as an unmapped key instead of a silent pass.
LOOP_FIELD_MAP: dict[str, str] = {
    "id": "LoopSpec.name",
    "name": "LoopSpec.name",
    "file": "LOOP.md",
    "goal": "LoopSpec.description",
    "cadence": "LoopSpec.cadence",
    "risk": "LoopSpec.autonomy",
    "tools": "claude-code (single runtime)",
    "skills": "platform/toolkits/*",
    "state": "STATE.md",
    "phases": "pf.loops.runner.run_loop",
    "human_gates": "loop-constraints.md + gate.yaml",
}


def check_loop_parity(root: Path) -> list[Finding]:
    """Every field upstream requires of a loop pattern has a counterpart here.

    Not instance validation — see the registry note. Upstream's cadence grammar
    is time-only and four of our loops are event-driven, so a literal check would
    force us to write "1d" where the truth is "pre-commit". Parity asks the
    question that actually matters: has upstream introduced a governance concept
    our catalogue has no answer for?
    """
    schema_path = root / "vendor" / "loop-engineering" / "patterns" / "registry.schema.json"
    if not schema_path.exists():
        return [Finding("error", "contract:loops", str(schema_path), "vendored schema missing")]
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    item = schema["properties"]["patterns"]["items"]
    required = list(item.get("required") or [])

    missing = [f for f in required if f not in LOOP_FIELD_MAP]
    out: list[Finding] = []
    for f in missing:
        out.append(Finding(
            "warning", "contract:loops", f,
            "newly required by loop-engineering's pattern schema and has no "
            "counterpart in LoopSpec — add one, or record why it does not apply"))

    stale = [f for f in LOOP_FIELD_MAP if f not in required
             and f not in (item.get("properties") or {})]
    for f in stale:
        out.append(Finding("info", "contract:loops", f,
                           "mapped here but no longer present upstream"))

    from pf.loops.registry import all_specs

    SPECS = all_specs()

    timed = [s for s in SPECS.values() if _is_timed(s.cadence)]
    out.append(Finding(
        "info", "contract:loops", "field parity",
        f"{len(required) - len(missing)}/{len(required)} upstream fields mapped; "
        f"{len(timed)}/{len(SPECS)} loops have a time cadence upstream could express"))
    return out


def _is_timed(cadence: str) -> bool:
    import re

    return bool(re.match(r"^(every\s+)?\d+[mhd]$|^(daily|hourly)$", cadence.strip()))


# ------------------------------------------------------------------ all ----
def verify(root: str | Path, project: tuple[str, str, Path] | None = None) -> Result:
    root = Path(root)
    ups = load_registry()
    findings = check_paths(root, ups)
    findings += check_otop(root, project[2] if project else None)
    findings += check_loop_parity(root)
    if project:
        g, p, d = project
        findings += check_mdl(root, d, g, p)
    else:
        # Graphs are generated and gitignored, so a fresh clone (and therefore
        # CI) has none. Silently skipping the MDL contract there would let the
        # one check that has already caught a real schema mistake quietly stop
        # running — visible only as a missing line nobody looks for.
        findings.append(Finding(
            "warning", "contract:mdl", "-",
            "not exercised: no project has a built graph. Run `pf seed <g> <p>` "
            "or `pf kg build` first, or pass a project explicitly"))
    n = sum(len(u.adopted) for u in ups) + 3
    return Result(findings=findings, checked=n)
