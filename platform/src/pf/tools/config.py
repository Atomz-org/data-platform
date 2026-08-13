"""Which tools a project actually runs — declared at the group, refined per project.

`registry.py` answers "what tools exist". This answers "what does *this* project
use", and the two are deliberately different questions: the UI lists everything
available while a project enables two of them.

## Why enablement is a file and not a directory check

Evidence BI decides it is enabled by asking whether `reporting/` exists. That
works until a tool has nothing to scaffold, or until someone deletes a generated
directory and silently turns the tool off. `tools.yaml` states the intent
directly, so "enabled but not yet bootstrapped" is a state the platform can see
and fix — which is exactly what `pf bootstrap` is for.

## Group over project

    groups/<group>/tools.yaml                      the family's decision
    groups/<group>/projects/<project>/tools.yaml   this entity's refinement

A tool enabled at the group is enabled for every sister. This is the whole point
of a group: sisters share infrastructure and differ only in business logic, so
"we review dbt changes with Recce" is a decision made once for the family rather
than re-argued per entity.

A project may override any key, including turning the tool off — an entity with
no dbt project has nothing to diff, and forcing it to carry the tool would mean
the group-level decision is a lie for one of its members. Config dicts deep-merge
so a project can change a port without restating the rest.

**A project reads its own group and nothing else.** There is no cross-group or
cross-sister resolution here, by construction: `resolve()` takes one group and
one project and never enumerates siblings.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

CONFIG_NAME = "tools.yaml"

HEADER = """\
# Which platform tools this {level} runs.
#
# Managed by `pf tool enable/disable`, but hand-editing is fine — it is read, not
# generated. A tool enabled here is scaffolded and bootstrapped by
# `pf bootstrap`, and contributes its assets to Dagster.
{extra}"""

GROUP_EXTRA = """\
# Enabled here means enabled for every sister project in this group. A project
# can override any key in its own tools.yaml, including `enabled: false`.
"""

PROJECT_EXTRA = """\
# Merged over the group's tools.yaml. Set `enabled: false` to opt this project
# out of something the group turned on.
"""


@dataclass(frozen=True)
class ToolConfig:
    """One tool's resolved settings for one project."""

    name: str
    enabled: bool = False
    config: dict[str, Any] = field(default_factory=dict)
    #: Where the enabling decision came from, for `pf tool list` to show.
    source: str = "default"


# ------------------------------------------------------------------- read --
def config_path(root: Path, group: str, project: str = "") -> Path:
    base = Path(root) / "groups" / group
    if project:
        base = base / "projects" / project
    return base / CONFIG_NAME


def load(path: Path) -> dict[str, Any]:
    """One tools.yaml, or an empty mapping. A missing file is not an error —
    most projects will never have one until a tool is enabled."""
    if not path.exists():
        return {}
    doc = yaml.safe_load(path.read_text()) or {}
    return doc.get("tools") or {}


def _merge(base: dict[str, Any], over: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge `over` onto a copy of `base`. Scalars and lists replace."""
    out = copy.deepcopy(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def resolve(root: Path, group: str, project: str) -> dict[str, ToolConfig]:
    """The effective tool config for one project: group defaults + its overrides."""
    group_raw = load(config_path(root, group))
    project_raw = load(config_path(root, group, project))

    out: dict[str, ToolConfig] = {}
    for name in sorted(set(group_raw) | set(project_raw)):
        g = group_raw.get(name) or {}
        p = project_raw.get(name) or {}
        merged = _merge(g if isinstance(g, dict) else {},
                        p if isinstance(p, dict) else {})
        # `source` is what makes an inherited setting explainable. Without it a
        # project shows "recce: on" with no way to tell whether that came from
        # here or from the group, which is the first question anyone asks.
        if name in project_raw and "enabled" in (p if isinstance(p, dict) else {}):
            source = "project"
        elif name in group_raw:
            source = "group"
        else:
            source = "project"
        out[name] = ToolConfig(
            name=name,
            enabled=bool(merged.get("enabled", False)),
            config=merged.get("config") or {},
            source=source,
        )
    return out


def enabled(root: Path, group: str, project: str) -> dict[str, ToolConfig]:
    """Only the tools this project actually runs."""
    return {n: c for n, c in resolve(root, group, project).items() if c.enabled}


def enabled_names(root: Path, group: str, project: str) -> list[str]:
    return sorted(enabled(root, group, project))


# ------------------------------------------------------------------ write --
def write(root: Path, group: str, project: str, name: str, *,
          on: bool | None = None, config: dict[str, Any] | None = None) -> Path:
    """Enable, disable or reconfigure one tool. Creates the file if needed.

    Writing at the group level (`project=""`) is how one decision reaches every
    sister. The YAML is rewritten wholesale, so any comment a human added below
    the header is lost — the header says as much, and the alternative (a
    comment-preserving round-trip) is a dependency this file does not need.
    """
    path = config_path(root, group, project)
    doc: dict[str, Any] = {}
    if path.exists():
        doc = yaml.safe_load(path.read_text()) or {}
    doc.setdefault("version", 1)
    tools = doc.setdefault("tools", {})
    entry = tools.setdefault(name, {})
    if on is not None:
        entry["enabled"] = bool(on)
    if config:
        entry["config"] = _merge(entry.get("config") or {}, config)

    level = "project" if project else "group"
    extra = PROJECT_EXTRA if project else GROUP_EXTRA
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(HEADER.format(level=level, extra=extra)
                    + yaml.safe_dump(doc, sort_keys=False))
    return path
