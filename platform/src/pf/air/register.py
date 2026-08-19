"""`air.yaml` — what an entity commits to — and the register derived from it.

## Why this is per-entity and not platform-wide

A risk register belongs to a company, not to shared infrastructure. That is the
constraint the `public-sector-ai-playbook` registry entry already states, and it
holds harder here: two sisters can run identical infra and face different
regulators, and a single platform-wide baseline would either be the union (every
project failing on a control that applies to one of them) or the intersection
(the strictest tenant silently unprotected).

    groups/<group>/air.yaml                       the family's baseline
    groups/<group>/projects/<project>/air.yaml    this entity's refinement

Group over project, deep-merged, exactly like `tools.yaml` — and for the same
reason, so `pf.tools.config._merge` is reused rather than re-derived.

## Declared, derived, and the line between them

`air.yaml` is **hand-written**: which controls this entity commits to, which it
has consciously accepted the absence of, and who owns that decision. None of it
is computable — "we accept no encryption at rest because there is no production
warehouse yet" is a judgement with a name attached.

`governance/air-register.md` is **generated** from `air.yaml` plus a coverage run,
and is on the gate denylist. Hand-editing it would make it disagree with the
declaration it came from, and the next regeneration would discard the edit — the
same argument that denies every other generated artefact in this platform.

## Attribution is not optional

The register is a derived artefact of a CC BY 4.0 work, so it carries the credit
line. `render_register` builds it in rather than trusting a template someone
might trim: an attribution you can forget to add is one you will forget to add,
and the obligation travels with the artefact a regulator is handed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import yaml

from pf.air.catalogue import Catalogue, absent_reason, available, load
from pf.air.coverage import Coverage, assess
from pf.tools.config import _merge

CONFIG_NAME = "air.yaml"
REGISTER_PATH = "governance/air-register.md"

#: Used when a catalogue declares no attribution of its own — an in-house or
#: public-domain control library. The register still says where its content came
#: from, because a governance artefact with no provenance is one nobody can check.
NO_ATTRIBUTION = "Control definitions are this platform's own."




class RegisterError(ValueError):
    """An `air.yaml` that cannot be honoured as written."""


# ------------------------------------------------------------------ config --
@dataclass(frozen=True)
class Acceptance:
    """A control consciously not taken, and who decided that.

    `reason` and `owner` are both required. An acceptance with no reason is a
    gap with better formatting, and an acceptance with no owner is one nobody can
    be asked about — which is the state this field exists to prevent.
    """

    control: str
    reason: str
    owner: str
    review_by: str = ""

    @property
    def overdue(self) -> bool:
        if not self.review_by:
            return False
        try:
            # UTC rather than local: a review date is a governance deadline, and
            # whether it has passed must not depend on the reviewer's timezone.
            return date.fromisoformat(self.review_by) < datetime.now(tz=UTC).date()
        except ValueError:
            return False


@dataclass(frozen=True)
class AirConfig:
    group: str = ""
    project: str = ""
    profile: dict[str, Any] = field(default_factory=dict)
    baseline: tuple[str, ...] = ()
    accepted: tuple[Acceptance, ...] = ()
    sources: tuple[str, ...] = ()

    @property
    def accepted_ids(self) -> frozenset[str]:
        return frozenset(a.control for a in self.accepted)

    def acceptance(self, control_id: str) -> Acceptance | None:
        return next((a for a in self.accepted if a.control == control_id), None)


def config_path(root: Path, group: str, project: str = "") -> Path:
    base = Path(root) / "groups" / group
    if project:
        base = base / "projects" / project
    return base / CONFIG_NAME


def _read(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_config(root: Path | str, group: str, project: str = "") -> AirConfig:
    """The effective declaration for one entity: group baseline + its refinement.

    `baseline` unions rather than replaces. A project that could shrink its
    family's commitments would make the group-level declaration advisory, and a
    baseline you can opt out of by editing your own file is not a baseline — the
    way to drop a control is `accepted:`, which requires a reason and an owner.
    """
    root = Path(root)
    group_doc = _read(config_path(root, group))
    proj_doc = _read(config_path(root, group, project)) if project else {}

    merged = _merge(group_doc, proj_doc)
    sources = [
        str(p.relative_to(root))
        for p in (config_path(root, group), config_path(root, group, project) if project else None)
        if p is not None and p.exists()
    ]

    baseline = tuple(
        dict.fromkeys(
            [*(str(c).upper() for c in (group_doc.get("baseline") or [])),
             *(str(c).upper() for c in (proj_doc.get("baseline") or []))]
        )
    )

    accepted: list[Acceptance] = []
    for raw in merged.get("accepted") or []:
        if not isinstance(raw, dict):
            raise RegisterError(f"{group}/{project}: an `accepted` entry must be a mapping")
        cid = str(raw.get("control", "")).upper()
        reason = str(raw.get("reason", "")).strip()
        owner = str(raw.get("owner", "")).strip()
        if not cid:
            raise RegisterError(f"{group}/{project}: an `accepted` entry has no `control`")
        if not reason:
            raise RegisterError(
                f"{group}/{project}: accepted {cid} has no `reason` — an acceptance "
                f"without one is a gap with better formatting"
            )
        if not owner:
            raise RegisterError(
                f"{group}/{project}: accepted {cid} has no `owner` — an acceptance "
                f"nobody owns is one nobody can be asked about"
            )
        accepted.append(Acceptance(cid, reason, owner, str(raw.get("review_by", "") or "")))

    return AirConfig(
        group=group,
        project=project,
        profile=merged.get("profile") or {},
        baseline=baseline,
        accepted=tuple(accepted),
        sources=tuple(sources),
    )


def validate(cfg: AirConfig, cat: Catalogue) -> list[str]:
    """Problems with a declaration that the catalogue can see. Empty is good."""
    out: list[str] = []
    for cid in cfg.baseline:
        if cid not in cat.controls:
            out.append(f"baseline names {cid}, which is not a control in the catalogue")
    for a in cfg.accepted:
        if a.control not in cat.controls:
            out.append(f"accepted names {a.control}, which is not a control in the catalogue")
        if a.control in cfg.baseline:
            out.append(
                f"{a.control} is both committed to in `baseline` and accepted as absent "
                f"— it cannot be both"
            )
        if a.overdue:
            out.append(f"acceptance of {a.control} was due for review on {a.review_by}")
    for key, value in (cfg.profile or {}).items():
        if not isinstance(value, str):
            out.append(f"profile.{key} should be a single value from the framework taxonomy")
    return out


# ------------------------------------------------------------------- gate --
@dataclass
class GateResult:
    """The blocking verdict: declared-baseline controls that are failing."""

    breaches: list[tuple[str, str]] = field(default_factory=list)
    warned: list[tuple[str, str]] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    assessed: int = 0
    vendored: bool = True

    @property
    def ok(self) -> bool:
        return not self.breaches and not self.problems

    @property
    def exit_code(self) -> int:
        return 1 if not self.ok else 0


def gate(root: Path | str, group: str, project: str, *, cov: Coverage | None = None) -> GateResult:
    """Block on a failing baseline control. `unexercised` warns and exits zero.

    That asymmetry is the ladder's rule and it is deliberate: walling a project
    off because a ledger has not been written yet is how a gate stops being run,
    while a control that is claimed and demonstrably not enforced is exactly what
    a baseline is for.
    """
    root = Path(root)
    if not available(root):
        # Not a breach. A clone without submodules cannot assess anything, and
        # failing the merge for it would punish the checkout, not the code.
        return GateResult(vendored=False)

    cat = load(root)
    cfg = load_config(root, group, project)
    problems = validate(cfg, cat)
    cov = cov or assess(root, group, project, catalogue=cat)

    breaches: list[tuple[str, str]] = []
    warned: list[tuple[str, str]] = []
    for cid in cfg.baseline:
        v = cov.get(cid)
        if v is None:
            continue
        if v.status == "fail":
            breaches.append((cid, v.check.evidence))
        elif v.status == "unexercised":
            warned.append((cid, v.check.evidence))
    return GateResult(breaches, warned, problems, len(cfg.baseline))


# --------------------------------------------------------------- rendering --
_MARK = {"pass": "✅", "fail": "❌", "unexercised": "⚠️"}


def render_register(root: Path | str, group: str, project: str) -> str:
    """The register, derived from `air.yaml` and a fresh coverage run."""
    root = Path(root)
    if not available(root):
        raise RegisterError(absent_reason(root))

    cat = load(root)
    cfg = load_config(root, group, project)
    cov = assess(root, group, project, catalogue=cat)
    problems = validate(cfg, cat)

    L: list[str] = []
    add = L.append
    add(f"# AI risk register — {group}/{project}")
    add("")
    add(
        "<!-- GENERATED by `pf air register`. Do not hand-edit: `air.yaml` is the "
        "declaration this is derived from, and the next run discards edits made "
        "here. This path is on the gate denylist. -->"
    )
    add("")
    add("_Derived from the repository on every run — no verdict below is stored._")
    add("")

    if cfg.profile:
        add("## System profile")
        add("")
        add("| dimension | value |")
        add("| --- | --- |")
        for k, v in cfg.profile.items():
            add(f"| {k} | {v} |")
        add("")

    counts = cov.counts
    add("## Coverage")
    add("")
    add(
        f"{counts['pass']} of {counts['total']} controls enforced · "
        f"{counts['fail']} not enforced · {counts['unexercised']} unexercised."
    )
    add("")

    add("### Committed baseline")
    add("")
    if not cfg.baseline:
        add("_Nothing declared. `pf air gate` cannot block on an empty baseline._")
    else:
        add("| | control | title | evidence |")
        add("| --- | --- | --- | --- |")
        for cid in cfg.baseline:
            v = cov.get(cid)
            ctl = cat.controls.get(cid)
            if v is None or ctl is None:
                add(f"| ❌ | {cid} | _not in catalogue_ | declaration is stale |")
                continue
            add(f"| {_MARK[v.status]} | {cid} | {ctl.title} | {v.check.evidence} |")
    add("")

    if cfg.accepted:
        add("### Accepted gaps")
        add("")
        add("| control | title | owner | review by | reason |")
        add("| --- | --- | --- | --- | --- |")
        for a in cfg.accepted:
            ctl = cat.controls.get(a.control)
            title = ctl.title if ctl else "_not in catalogue_"
            due = f"{a.review_by}{' ⚠️ overdue' if a.overdue else ''}" if a.review_by else "—"
            add(f"| {a.control} | {title} | {a.owner} | {due} | {a.reason.strip()} |")
        add("")

    other = [
        v
        for v in cov
        if v.id not in cfg.baseline and v.id not in cfg.accepted_ids
    ]
    if other:
        add("### Not in the baseline")
        add("")
        add("_Reported, advisory. These do not block a merge._")
        add("")
        add("| | control | title | evidence |")
        add("| --- | --- | --- | --- |")
        for v in other:
            add(f"| {_MARK[v.status]} | {v.id} | {v.control.title} | {v.check.evidence} |")
        add("")

    regimes = cov.regimes()
    if regimes:
        add("### By external regime")
        add("")
        add("_Counted from the same verdicts above, so it cannot disagree with them._")
        add("")
        add("| regime | enforced | not enforced | unexercised |")
        add("| --- | --- | --- | --- |")
        for name, c in regimes.items():
            title = cat.regimes[name].title if name in cat.regimes else name
            add(f"| {title} | {c['pass']} | {c['fail']} | {c['unexercised']} |")
        add("")

    if problems:
        add("### Problems with this declaration")
        add("")
        for p in problems:
            add(f"- {p}")
        add("")

    add("---")
    add("")
    add(f"Catalogue pinned at `{cov.commit[:12] or 'unknown'}`.")
    add("")
    # Every catalogue that contributed, in its own words. Collected from the
    # sources actually loaded rather than templated, so an obligation cannot be
    # dropped by forgetting to update a string.
    for line in (cat.attributions or (NO_ATTRIBUTION,)):
        add(line)
        add("")
    add("")
    return "\n".join(L)


def write_register(root: Path | str, group: str, project: str) -> Path:
    root = Path(root)
    text = render_register(root, group, project)
    out = root / "groups" / group / "projects" / project / REGISTER_PATH
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    return out
