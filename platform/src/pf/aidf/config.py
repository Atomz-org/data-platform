"""The resolved governance configuration for one entity, and the rule that it
may only ever tighten.

Three layers, each read if it exists, each laid over the one before:

    platform/src/pf/aidf/data/defaults.yaml       the floor, every entity
    groups/<group>/aidf.yaml                       the family
    groups/<group>/projects/<project>/governance/aidf.yaml   the entity

The merge is not a plain dict update. The same invariant `policy.yaml` overlays
live under applies here: a lower layer can add a validator, shorten a patch
window, lower a budget or mark an article out of scope with a reason — and it
cannot do the reverse. `AidfRelaxation` is raised at load time rather than at
audit time, because a loosening that only shows up in a nightly report is a
loosening that has already been in force for a day.

Why a separate file from `governance/policy.yaml`: that file is the *ontology*
policy layer (intents and constraints over classes and roles, `pf semantic
policy`). This one is the runtime layer — who may write what through the
governance engine, and what the DORA audit checks for this entity. They answer
different questions and are loaded by different code; sharing a file would make
each loader skip half of it.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

DATA_DIR = Path(__file__).parent / "data"
DEFAULTS_FILE = DATA_DIR / "defaults.yaml"

#: Project-relative location of the entity's own overlay.
PROJECT_FILE = "governance/aidf.yaml"
#: Group-relative location of the family overlay.
GROUP_FILE = "aidf.yaml"


class AidfConfigError(ValueError):
    """The overlay is malformed — a key the schema does not know, a wrong type."""


class AidfRelaxation(AidfConfigError):
    """An overlay tried to loosen the floor. Named separately so a caller can
    tell a typo from a policy decision it must refuse."""


# --------------------------------------------------------------- layering --
#: Numeric keys that may only decrease. Dotted paths into the merged document.
_ONLY_DOWN = (
    "runtime.budgets.max_iterations_per_invocation",
    "runtime.budgets.max_consecutive_validation_failures",
    "dora.prowler.fail_on.critical",
    "dora.prowler.fail_on.high",
    "dora.prowler.fail_on.medium",
    "dora.sbom.grace_days.critical",
    "dora.sbom.grace_days.high",
    "dora.sbom.grace_days.medium",
    "dora.sbom.grace_days.low",
)
#: Lists that may only grow. An overlay's entries are unioned in.
_ONLY_GROW = (
    "runtime.validators",
    "runtime.system_schemas",
    "runtime.elevated.paths",
    "dora.sbom.severity",
    "dora.extra_providers",
)
#: Booleans that may only be switched *on* (True is the stricter state).
_ONLY_ON = ("runtime.budgets.trip_circuit_breaker_on_breach",)
#: Booleans that may only be switched *off* (False is the stricter state:
#: `ignore_unfixed: false` blocks on vulnerabilities nobody can patch yet).
_ONLY_OFF = ("dora.sbom.ignore_unfixed",)
_SEVERITY_ORDER = ("informational", "low", "medium", "high", "critical")


def _get(doc: dict[str, Any], dotted: str) -> Any:
    node: Any = doc
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def _set(doc: dict[str, Any], dotted: str, value: Any) -> None:
    parts = dotted.split(".")
    node = doc
    for part in parts[:-1]:
        node = node.setdefault(part, {})
    node[parts[-1]] = value


def _deep_merge(base: dict[str, Any], over: dict[str, Any], path: str = "") -> None:
    """Plain recursive merge for everything the tighten rules do not name."""
    for key, value in over.items():
        here = f"{path}.{key}" if path else key
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value, here)
        else:
            base[key] = copy.deepcopy(value)


def _apply_layer(merged: dict[str, Any], over: dict[str, Any], source: str) -> None:
    """Lay `over` onto `merged`, refusing anything that loosens."""
    if not isinstance(over, dict):
        raise AidfConfigError(f"{source}: top level must be a mapping")
    unknown = set(over) - {"version", "runtime", "dora"}
    if unknown:
        raise AidfConfigError(f"{source}: unknown top-level key(s) {sorted(unknown)}")

    # Numeric ceilings.
    for dotted in _ONLY_DOWN:
        new = _get(over, dotted)
        if new is None:
            continue
        cur = _get(merged, dotted)
        if not isinstance(new, int) or isinstance(new, bool) or new < 0:
            raise AidfConfigError(f"{source}: {dotted} must be a non-negative integer")
        if cur is not None and new > cur:
            raise AidfRelaxation(f"{source}: {dotted} may not rise from {cur} to {new}")

    # Grow-only lists: union, never replace.
    for dotted in _ONLY_GROW:
        new = _get(over, dotted)
        if new is None:
            continue
        if not isinstance(new, list):
            raise AidfConfigError(f"{source}: {dotted} must be a list")
        cur = list(_get(merged, dotted) or [])
        _set(over, dotted, cur + [x for x in new if x not in cur])

    # On-only booleans.
    for dotted in _ONLY_ON:
        new = _get(over, dotted)
        if new is None:
            continue
        if not isinstance(new, bool):
            raise AidfConfigError(f"{source}: {dotted} must be true or false")
        if _get(merged, dotted) is True and new is False:
            raise AidfRelaxation(f"{source}: {dotted} may not be switched off")
    for dotted in _ONLY_OFF:
        new = _get(over, dotted)
        if new is None:
            continue
        if not isinstance(new, bool):
            raise AidfConfigError(f"{source}: {dotted} must be true or false")
        if _get(merged, dotted) is False and new is True:
            raise AidfRelaxation(f"{source}: {dotted} may not be switched back on")

    # Severity threshold may only go down the scale (i.e. catch more).
    new_thr = _get(over, "dora.prowler.severity_threshold")
    if new_thr is not None:
        cur_thr = _get(merged, "dora.prowler.severity_threshold")
        if str(new_thr).lower() not in _SEVERITY_ORDER:
            raise AidfConfigError(f"{source}: unknown severity {new_thr!r}")
        if cur_thr and _SEVERITY_ORDER.index(str(new_thr).lower()) > _SEVERITY_ORDER.index(str(cur_thr).lower()):
            raise AidfRelaxation(f"{source}: dora.prowler.severity_threshold may not rise above {cur_thr}")

    # Taking an entity out of scope, or an article out of scope, needs a reason
    # and an owner. It is allowed — DORA does not apply to everyone — but never
    # silently.
    if _get(over, "dora.in_scope") is False:
        if not (_get(over, "dora.out_of_scope_reason") or _get(merged, "dora.out_of_scope_reason")):
            raise AidfRelaxation(f"{source}: dora.in_scope: false needs dora.out_of_scope_reason and dora.owner")
        if not (_get(over, "dora.owner") or _get(merged, "dora.owner")):
            raise AidfRelaxation(f"{source}: dora.in_scope: false needs dora.owner")
    for art, spec in (_get(over, "dora.articles") or {}).items():
        if not isinstance(spec, dict):
            raise AidfConfigError(f"{source}: dora.articles.{art} must be a mapping")
        if spec.get("applies") is False and not (spec.get("reason") and spec.get("owner")):
            raise AidfRelaxation(f"{source}: dora.articles.{art}.applies: false needs reason and owner")

    # Exceptions are dated and owned or they are not exceptions.
    for i, exc in enumerate(_get(over, "dora.sbom.exceptions") or []):
        missing = [k for k in ("id", "reason", "owner", "expires") if not (isinstance(exc, dict) and exc.get(k))]
        if missing:
            raise AidfConfigError(f"{source}: dora.sbom.exceptions[{i}] is missing {missing}")

    _deep_merge(merged, over)


# ----------------------------------------------------------------- loading --
@dataclass(frozen=True)
class AidfConfig:
    """The resolved document plus where each layer came from."""

    group: str
    project: str
    doc: dict[str, Any]
    layers: tuple[str, ...] = field(default_factory=tuple)

    # -- runtime --
    @property
    def runtime(self) -> dict[str, Any]:
        return self.doc.get("runtime", {})

    @property
    def dialect(self) -> str:
        return str(self.runtime.get("sql_dialect") or "duckdb")

    @property
    def mart_pattern(self) -> str:
        return str(self.runtime.get("mart_pattern"))

    @property
    def validators(self) -> tuple[str, ...]:
        return tuple(self.runtime.get("validators") or ("schema",))

    @property
    def roles(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for role, spec in (self.runtime.get("roles") or {}).items():
            targets = spec.get("targets", []) if isinstance(spec, dict) else list(spec or [])
            out[str(role)] = [str(t) for t in targets]
        return out

    @property
    def elevated_paths(self) -> list[str]:
        return list((self.runtime.get("elevated") or {}).get("paths") or [])

    @property
    def elevated_roles(self) -> list[str]:
        return list((self.runtime.get("elevated") or {}).get("roles") or [])

    @property
    def budgets(self) -> dict[str, Any]:
        return dict(self.runtime.get("budgets") or {})

    # -- dora --
    @property
    def dora(self) -> dict[str, Any]:
        return self.doc.get("dora", {})

    @property
    def in_scope(self) -> bool:
        return bool(self.dora.get("in_scope", True))

    @property
    def provider(self) -> str:
        return str(self.dora.get("provider") or "")

    @property
    def providers(self) -> list[str]:
        """The cloud first, then every extra provider, each once."""
        out = [self.provider] if self.provider else []
        out += [str(p) for p in (self.dora.get("extra_providers") or []) if str(p) not in out]
        return out

    def article_applies(self, article_id: str) -> tuple[bool, str]:
        spec = (self.dora.get("articles") or {}).get(str(article_id)) or {}
        if spec.get("applies") is False:
            return False, str(spec.get("reason") or "")
        return True, ""

    def to_yaml(self) -> str:
        return yaml.safe_dump(self.doc, sort_keys=False, width=88)


def defaults() -> dict[str, Any]:
    return yaml.safe_load(DEFAULTS_FILE.read_text(encoding="utf-8")) or {}


def layer_paths(root: Path, group: str, project: str) -> list[Path]:
    """Where the overlays would be, whether or not they exist. Floor first."""
    out = [DEFAULTS_FILE]
    if group:
        out.append(root / "groups" / group / GROUP_FILE)
    if group and project:
        out.append(root / "groups" / group / "projects" / project / PROJECT_FILE)
    return out


def load(root: Path, group: str = "", project: str = "") -> AidfConfig:
    """Resolve the configuration for an entity. Works with no overlay at all —
    a project scaffolded before this capability existed is governed by the
    floor, not ungoverned."""
    merged = defaults()
    layers: list[str] = [str(DEFAULTS_FILE.relative_to(Path(__file__).parents[3]))]
    for path in layer_paths(root, group, project)[1:]:
        if not path.exists():
            continue
        try:
            over = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            raise AidfConfigError(f"{path}: {exc}") from exc
        rel = str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
        _apply_layer(merged, over, rel)
        layers.append(rel)
    return AidfConfig(group=group, project=project, doc=merged, layers=tuple(layers))


def entities(root: Path) -> list[tuple[str, str]]:
    """Every (group, project) in the checkout, for the CI-wide checks."""
    out: list[tuple[str, str]] = []
    groups = root / "groups"
    if not groups.is_dir():
        return out
    for g in sorted(p for p in groups.iterdir() if p.is_dir() and not p.name.startswith(".")):
        projects = g / "projects"
        if not projects.is_dir():
            continue
        out.extend((g.name, p.name) for p in sorted(projects.iterdir())
                   if p.is_dir() and not p.name.startswith("."))
    return out
