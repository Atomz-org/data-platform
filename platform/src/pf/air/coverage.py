"""Coverage — which controls this platform actually discharges, derived on read.

## The rule

**Nothing here is stored.** A verdict is computed from the repository every time
it is asked for, because a recorded pass survives the change that invalidated it.
That is the same rule `pf.onboard.ladder` states for the onboarding ladder, and
this module shares its vocabulary (`pf.checks`) for the same reason: a control
report and a stage gate answer the same kind of question.

## How a control gets its verdict

A control is discharged by a *policy* — an entry in
`platform/src/pf/ontology/policy.yaml` naming this control in its `controls:`
list. The policy names an `enforced_by` artefact. The verdict is about that
artefact, not about anybody's intent:

    fail          no policy claims the control, or every claiming policy has an
                  empty `enforced_by` (`Ontology.unenforced_policies()` — a
                  control that exists only on paper), or the artefact it names
                  does not resolve on disk
    unexercised   the artefact resolves, but nothing shows it has ever run — the
                  evidence it declares has produced nothing
    pass          the artefact resolves, and its evidence exists

Only `fail` closes a gate. `unexercised` is reported loudly and exits zero,
because walling a project off over a ledger that has not been written yet is how
a gate stops being run at all.

## Why an artefact check and not a test

`enforced_by` is a claim in YAML, and YAML cannot be wrong in a way anyone
notices. Resolving `pf.provenance.ledger:decision` to an actual importable symbol
and `gate.yaml:denylist` to an actual section is what turns the claim into
something that breaks when it stops being true — a renamed function demotes its
control to `fail` at the next `pf air coverage`, rather than at the next audit.
"""

from __future__ import annotations

import importlib
import inspect
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any

import yaml

from pf.air.catalogue import Catalogue, Control, absent_reason, available, load
from pf.checks import Check, failed, passed, unexercised

#: Evidence kinds whose output is a file we can look for. Anything not listed is
#: a command a human runs (`pf check`, `pf gate`), which we cannot prove has run
#: from the filesystem — those make a control `pass` on the artefact alone.
_EVIDENCE_FILES: dict[str, tuple[str, ...]] = {
    "STATE.md": ("STATE.md",),
    "loop-ledger.json": ("loop-ledger.json",),
    "impact_reports": ("impact_reports",),
    "kg/context_card.md": ("**/kg/context_card.md",),
    "pf provenance verify": ("provenance/chain.jsonl",),
    "governance/air-register.md": ("**/governance/air-register.md",),
}


@dataclass(frozen=True)
class Claim:
    """One policy's claim on one control, and whether its artefact resolves."""

    policy_id: str
    artefact: str
    resolves: bool
    detail: str = ""


@dataclass(frozen=True)
class ControlVerdict:
    """A control, its check, and the claims the check was built from."""

    control: Control
    check: Check
    claims: tuple[Claim, ...] = ()
    policies: tuple[str, ...] = ()

    @property
    def id(self) -> str:
        return self.control.id

    @property
    def status(self) -> str:
        return self.check.status

    @property
    def ok(self) -> bool:
        return self.check.ok


@dataclass
class Coverage:
    """The whole assessment. `vendored=False` means every verdict is unexercised."""

    verdicts: list[ControlVerdict] = field(default_factory=list)
    vendored: bool = True
    reason: str = ""
    commit: str = ""

    def __iter__(self):
        return iter(self.verdicts)

    def __len__(self) -> int:
        return len(self.verdicts)

    def get(self, control_id: str) -> ControlVerdict | None:
        target = control_id.strip().upper()
        return next((v for v in self.verdicts if v.id == target), None)

    def of_status(self, status: str) -> list[ControlVerdict]:
        return [v for v in self.verdicts if v.status == status]

    @cached_property
    def passing(self) -> list[ControlVerdict]:
        return self.of_status("pass")

    @cached_property
    def failing(self) -> list[ControlVerdict]:
        return self.of_status("fail")

    @cached_property
    def unexercised(self) -> list[ControlVerdict]:
        return self.of_status("unexercised")

    @property
    def counts(self) -> dict[str, int]:
        return {
            "pass": len(self.passing),
            "fail": len(self.failing),
            "unexercised": len(self.unexercised),
            "total": len(self.verdicts),
        }

    def regimes(self) -> dict[str, dict[str, int]]:
        """Coverage rolled up per external regime.

        This is the number an assessor asks for — "how much of the EU AI Act do
        you cover" — and it is deliberately computed from the same verdicts
        rather than tracked separately, so it cannot disagree with them.
        """
        out: dict[str, dict[str, int]] = {}
        for v in self.verdicts:
            for fw in v.control.frameworks:
                bucket = out.setdefault(fw, {"pass": 0, "fail": 0, "unexercised": 0})
                bucket[v.status] += 1
        return dict(sorted(out.items()))


# ------------------------------------------------------------- resolution --
def _resolve_artefact(root: Path, spec: str) -> tuple[bool, str]:
    """Does the thing `enforced_by` names actually exist?

    Three forms appear in `policy.yaml`, and all three are resolved literally:

        pf.provenance.ledger:decision   dotted module:symbol — imported
        gate.yaml:denylist              file:section — file read, key checked
        platform/hooks/pre_tool_use.py  plain path — file exists
    """
    spec = spec.strip()
    if not spec:
        return False, "empty"

    # file:section — a YAML policy file and a key inside it. Distinguished from
    # `module:symbol` by the head having a file extension, not by guessing.
    head, _, section = spec.partition(":")
    if head.endswith((".yaml", ".yml", ".json")):
        p = root / head
        if not p.exists():
            return False, f"{head} not found"
        if not section:
            return True, head
        try:
            doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except Exception as exc:  # noqa: BLE001
            return False, f"{head} unreadable: {exc}"
        if isinstance(doc, dict) and section in doc:
            return True, f"{head}:{section}"
        return False, f"{head} has no section '{section}'"

    # dotted module:name
    if ":" in spec:
        mod, _, attr = spec.partition(":")
        try:
            m = importlib.import_module(mod)
        except Exception as exc:  # noqa: BLE001 — an unimportable artefact is the finding
            return False, f"{mod} will not import ({type(exc).__name__})"

        # `pf.tools.spec:Tool.gate_sections` — a symbol, possibly a method on a
        # class in that module.
        obj: Any = m
        for part in attr.split("."):
            obj = getattr(obj, part, None)
            if obj is None:
                break
        if obj is not None:
            return True, spec

        # `pf.ontology.validate:money-without-currency` — not a symbol at all.
        # `policy.yaml` also names *rule ids*: the code a check emits on its
        # `ValidationIssue`, which is a string literal in the module rather than
        # an attribute (and is hyphenated, so it could never be one). Looking for
        # the literal in the source is the honest resolution of that form, and it
        # keeps its failure mode: deleting the check deletes the literal, and the
        # control it discharges goes red at the next `pf air coverage`.
        if not attr.replace(".", "_").isidentifier():
            try:
                src = inspect.getsource(m)
            except (OSError, TypeError):
                return False, f"{mod} source unavailable; cannot resolve rule '{attr}'"
            if attr in src:
                return True, spec
            return False, f"{mod} emits no rule '{attr}'"
        return False, f"{mod} has no {attr}"

    # plain path
    p = root / spec
    if p.exists():
        return True, spec
    return False, f"{spec} not found"


def _evidence_seen(root: Path, kinds: list[str]) -> tuple[bool, str]:
    """Has anything this policy declares as evidence actually been produced?

    Only file-shaped evidence can be answered from the filesystem. A policy whose
    evidence is entirely command-shaped (`pf check`) returns True with a note —
    we cannot prove a command has run and will not pretend to.
    """
    checkable = [k for k in kinds if k in _EVIDENCE_FILES]
    if not checkable:
        return True, "evidence is command-shaped; not checkable from disk"
    for kind in checkable:
        for pattern in _EVIDENCE_FILES[kind]:
            if "*" in pattern:
                if next(root.glob(pattern), None) is not None:
                    return True, kind
            elif (root / pattern).exists():
                return True, kind
    return False, f"declared evidence has produced nothing: {', '.join(checkable)}"


# ----------------------------------------------------------------- assess --
def assess(
    root: Path | str,
    group: str = "",
    project: str = "",
    *,
    catalogue: Catalogue | None = None,
) -> Coverage:
    """One verdict per control in the catalogue. Re-derived every call.

    `group`/`project` select the ontology: a group may extend the platform's
    policies, so a sister company can discharge a control the shared runtime does
    not. Absent both, the platform ontology is assessed on its own.
    """
    root = Path(root)
    if catalogue is None:
        if not available(root):
            return Coverage(vendored=False, reason=absent_reason(root))
        catalogue = load(root)

    onto = _ontology(root, group)
    verdicts: list[ControlVerdict] = []

    for control in catalogue.sorted_controls:
        policies = onto.policies_for_control(control.id)
        if not policies:
            verdicts.append(
                ControlVerdict(
                    control,
                    failed(control.id, "no policy in policy.yaml claims this control"),
                )
            )
            continue

        claims: list[Claim] = []
        for p in policies:
            if not p.enforced_by:
                claims.append(Claim(p.id, "", False, "policy has no enforced_by"))
                continue
            for artefact in p.enforced_by:
                ok, detail = _resolve_artefact(root, artefact)
                claims.append(Claim(p.id, artefact, ok, detail))

        resolved = [c for c in claims if c.resolves]
        names = tuple(p.id for p in policies)

        if not resolved:
            broken = "; ".join(f"{c.policy_id}: {c.detail}" for c in claims) or "none"
            verdicts.append(
                ControlVerdict(
                    control,
                    failed(control.id, f"claimed but not enforced — {broken}"),
                    tuple(claims),
                    names,
                )
            )
            continue

        evidence_kinds = [e for p in policies for e in p.evidence]
        seen, note = _evidence_seen(root, evidence_kinds)
        artefacts = ", ".join(sorted({c.artefact for c in resolved}))
        if seen:
            verdicts.append(
                ControlVerdict(
                    control,
                    passed(control.id, f"{artefacts} ({', '.join(names)})"),
                    tuple(claims),
                    names,
                )
            )
        else:
            verdicts.append(
                ControlVerdict(
                    control,
                    unexercised(control.id, f"{artefacts} resolves, but {note}"),
                    tuple(claims),
                    names,
                )
            )

    return Coverage(verdicts=verdicts, commit=catalogue.commit)


def _ontology(root: Path, group: str):
    """The platform ontology, with a group's extension merged over it if there is one.

    A group may add policies the shared runtime does not have — a tenant with a
    regulator the platform has never met — so its controls must be assessable
    without those policies leaking into every other sister's coverage. A group
    with no extension file is the ordinary case, not an error.
    """
    from pf.ontology.model import load_group_ontology, load_ontology

    if group:
        try:
            return load_group_ontology(root, group)
        except Exception:  # noqa: BLE001 — a group without an extension is ordinary
            pass
    return load_ontology()
