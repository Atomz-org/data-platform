"""Pluggable tools: one declaration, wired everywhere.

    from pf.tools import all_tools, enabled, bootstrap_tools, dagster_contributions

`spec` defines the contract, `registry` finds tools, `config` decides which ones
a project runs. This module is the seam every *consumer* calls, so the scaffolder,
the bootstrap list, the Dagster factory, the CLI and the UI each know about
"tools" in general and about no tool in particular.

## Adding a tool

Inside this repo: a module under `pf/tools/` exporting `TOOL`, plus its name in
`registry.BUILTIN_MODULES`. `pf.tools.recce` is the reference.

Outside it: any installed distribution advertising a `pf.tools` entry point.

    [project.entry-points."pf.tools"]
    elementary = "pf_tool_elementary:TOOL"

Nothing in this repo changes for the second case. That is the whole point — the
platform grows sideways by installation rather than by edit.

## Reaching every project

A tool enabled in `groups/<group>/tools.yaml` is enabled for every sister.
`pf bootstrap --all` then walks every project and runs each enabled tool's
bootstrap hook, which is the same mechanism that retrofits any platform step onto
projects created before it existed. There is no separate "roll it out" path to
forget.

## On embedding a tool UI in Dagster

Dagster OSS has no extension point for adding a tab or an iframe to its web UI —
`dagster-webserver` serves a fixed React bundle, and asset metadata is the only
operator-facing surface a code location can write into. So a tool's UI reaches
Dagster two ways, both real and neither a custom tab:

  * the tool's work is a **real asset** in the graph, with lineage into the models
    it reviews, so it appears in Dagster's asset view and run timeline; and
  * each run attaches `MetadataValue.md` (the diff summary, rendered inline by
    Dagster) and `MetadataValue.url` (a deep link to the tool's own server).

The single pane that shows both at once is `pf ui` → **Review**, which embeds the
tool's server next to the lineage and impact this platform already tracks. That
is a deliberate placement, not a workaround: the control plane is ours to extend
and Dagster's UI is not.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pf.tools.config import (
    ToolConfig,
    config_path,
    enabled,
    enabled_names,
    resolve,
    write,
)
from pf.tools.registry import (
    DiscoveryError,
    all_tools,
    discover,
    for_scope,
    get,
    register_capabilities,
    tool_capabilities,
)
from pf.tools.spec import (
    DbtBinding,
    InvalidTool,
    Requirement,
    Surface,
    Tool,
    ToolContext,
    ToolContribution,
)

__all__ = [
    "DbtBinding", "DiscoveryError", "InvalidTool", "Requirement", "Surface",
    "Tool", "ToolConfig", "ToolContext", "ToolContribution",
    "all_tools", "bootstrap_tools", "config_path", "dagster_contributions",
    "discover", "enabled", "enabled_names", "for_scope", "get", "readiness",
    "register_capabilities", "resolve", "stack_layers", "tool_capabilities",
    "write",
]


def _project_dir(root: Path, group: str, project: str) -> Path:
    return Path(root) / "groups" / group / "projects" / project


# -------------------------------------------------------------- bootstrap --
def bootstrap_order(enabled_cfg: dict[str, Any],
                    tools: dict[str, Any]) -> list[tuple[str, Any]]:
    """Enabled tools in dependency order — every `Tool.after` before its dependant.

    Alphabetical within a level, so the order is stable and a diff of bootstrap
    output does not move when an unrelated tool is installed.

    A cycle cannot deadlock the scaffolder: when nothing is left that has all
    its predecessors satisfied, the remainder is emitted alphabetically. A tool
    graph is three or four nodes declared in this repository, so a cycle is a
    bug to notice rather than a condition to handle gracefully — but it must not
    be the reason `pf new-project` hangs.
    """
    pending = dict(sorted(enabled_cfg.items()))
    done: set[str] = set()
    out: list[tuple[str, Any]] = []
    while pending:
        ready = [
            n for n in pending
            # An `after` naming a tool that is not enabled here is satisfied:
            # ordering behind something absent is not a reason to refuse to run.
            if all(dep in done or dep not in pending
                   for dep in getattr(tools.get(n), "after", ()) or ())
        ]
        if not ready:
            ready = list(pending)
        for n in ready:
            out.append((n, pending.pop(n)))
            done.add(n)
    return out


def _apply_capability(tool: Any, root: Path, group: str, project: str,
                      d: Path) -> Any | None:
    """Backfill one enabled tool's capability — files, settings, gate rules.

    This is what makes enabling a tool in `tools.yaml` *sufficient*: a project
    scaffolded into a group whose family already decided on a tool gets that
    tool's docs, permissions and gate rules from plain `pf bootstrap`, with no
    separate `pf tool enable` pass to remember. `pf.capabilities.defaults()`
    deliberately excludes tool capabilities so they are not applied twice; this
    is the single place that applies them, keyed on the same decision
    (`tools.yaml`) that drives every other tool consumer.

    Same all-or-nothing rule as `_bootstrap_capabilities`, for the same reason:
    `apply` rewrites targets wholesale, and a partially-present capability
    means somebody edited one of its files — rewriting that is a decision for
    `pf tool enable`, taken deliberately, not for a background retrofit.

    Returns a StepResult when something happened or is blocked; None when the
    capability is fully present, which is the steady state and not worth a row.
    """
    from pf.capabilities import apply as apply_cap
    from pf.capabilities import gate_additions, render
    from pf.scaffold.bootstrap import StepResult

    cap = tool.capability
    if cap is None or not cap.files:
        return None
    # `.github/**` belongs to the repository, not the project — the same split
    # `pf.capabilities.apply` makes when writing.
    rendered = [render(rel, {"group": group, "project": project,
                             "module": project.replace("-", "_")})
                for rel in cap.files]
    targets = [(root if rel.startswith(".github/") else d) / rel
               for rel in rendered]
    present = [t for t in targets if t.exists()]
    if len(present) == len(targets):
        return None
    if present:
        return StepResult(
            f"tool:{tool.name}", "skipped",
            f"capability {len(present)}/{len(targets)} file(s) already exist — "
            f"`pf tool enable {tool.name} {group} {project}` to apply deliberately")
    ctx = {"group": group, "project": project, "module": project.replace("-", "_")}
    written = apply_cap(cap, root, d, ctx)
    # The gate half travels with the files, or the capability is present with
    # its guard rail absent — the exact failure `_bootstrap_capabilities` names.
    from pf.cli import _merge_gate_rules
    _merge_gate_rules(gate_additions([cap]))
    return StepResult(f"tool:{tool.name}", "ok",
                      f"capability applied ({len(written)} file(s))")


def bootstrap_tools(root: Path, group: str, project: str) -> list[Any]:
    """Run every enabled tool's bootstrap hook. Idempotent, never raises.

    A tool that is enabled but not installed is *skipped*, not failed: enabling
    a tool is a decision about the project, installing it is a fact about the
    machine, and a laptop without the extra should not turn every project red.

    Unless it declares `offline`, in which case the hook runs anyway.
    A bootstrap that only projects the project into a file needs nothing
    installed, and skipping it made the artefacts depend on which machine ran
    the scaffolder — the one thing scaffolding must not do.

    Before each hook, the tool's *capability* is backfilled if wholly absent
    (see `_apply_capability`) — capability first, because the hook may assume
    the settings and docs the capability writes.
    """
    from pf.scaffold.bootstrap import StepResult

    results: list[Any] = []
    tools = all_tools()
    d = _project_dir(root, group, project)

    for name, cfg in bootstrap_order(enabled(root, group, project), tools):
        tool = tools.get(name)
        if tool is None:
            results.append(StepResult(f"tool:{name}", "failed",
                                      "enabled but not registered"))
            continue
        try:
            cap_result = _apply_capability(tool, root, group, project, d)
            if cap_result is not None:
                results.append(cap_result)
        except Exception as exc:  # noqa: BLE001 — a broken capability is data
            results.append(StepResult(f"tool:{name}", "failed",
                                      f"capability: {type(exc).__name__}: {exc}"[:160]))
            continue
        missing = tool.missing()
        if missing and not tool.offline:
            results.append(StepResult(
                f"tool:{name}", "skipped",
                "not installed — " + ", ".join(
                    m.hint or m.describe() for m in missing[:2])))
            continue
        try:
            hook = tool.hook("bootstrap")
        except Exception as exc:  # noqa: BLE001 — a broken hook is data
            results.append(StepResult(f"tool:{name}", "failed",
                                      f"{type(exc).__name__}: {exc}"[:160]))
            continue
        if hook is None:
            results.append(StepResult(f"tool:{name}", "ok", "nothing to bootstrap"))
            continue
        try:
            r = hook(root, group, project, d, cfg.config)
            results.append(r if r is not None
                           else StepResult(f"tool:{name}", "ok", ""))
        except Exception as exc:  # noqa: BLE001
            results.append(StepResult(f"tool:{name}", "failed",
                                      f"{type(exc).__name__}: {exc}"[:160]))
    return results


# ---------------------------------------------------------------- dagster --
def dagster_contributions(root: Path, group: str, project: str,
                          project_dir: Path | None = None,
                          dbt_dir: Path | None = None,
                          warehouse: Any = None) -> list[ToolContribution]:
    """Every enabled tool's Dagster contribution.

    Failures are swallowed to a warning rather than raised. A code location that
    cannot load takes the whole project out of Dagster, and a broken optional
    tool is not worth that — the project's own assets must keep running.
    """
    import warnings

    d = Path(project_dir) if project_dir else _project_dir(root, group, project)
    tools = all_tools()
    out: list[ToolContribution] = []

    for name, cfg in sorted(enabled(root, group, project).items()):
        tool = tools.get(name)
        # `offline` tools contribute even with a requirement missing: their
        # assets do not drive the binary. Gating on `missing()` alone made a
        # container without the `metadata` CLI serve every code location with
        # the catalogue asset quietly gone, which reads as "the tool is off".
        if tool is None or (tool.missing() and not tool.offline):
            continue
        try:
            hook = tool.hook("dagster")
            if hook is None:
                continue
            ctx = ToolContext(
                root=Path(root), group=group, project=project, project_dir=d,
                dbt_dir=Path(dbt_dir) if dbt_dir else d / "transform",
                warehouse=warehouse, config=dict(cfg.config),
            )
            out.append(hook(ctx))
        except Exception as exc:  # noqa: BLE001 — never break a code location
            warnings.warn(f"tool '{name}' contributed nothing to Dagster: "
                          f"{type(exc).__name__}: {exc}", stacklevel=2)
    return out


# -------------------------------------------------------------- readiness --
def readiness(root: Path, group: str, project: str) -> list[dict[str, Any]]:
    """Per-tool status for `pf tool doctor` and the UI.

    Reports the whole chain in one place — registered, enabled, installed, dbt
    prerequisites met — because "why is this tool not doing anything" is
    otherwise four separate investigations.
    """
    d = _project_dir(root, group, project)
    resolved = resolve(root, group, project)
    rows: list[dict[str, Any]] = []

    for name, tool in sorted(all_tools().items()):
        cfg = resolved.get(name)
        row: dict[str, Any] = {
            "name": name,
            "title": tool.title,
            "summary": tool.summary,
            "url": tool.url,
            "scope": sorted(tool.scope),
            "enabled": bool(cfg and cfg.enabled),
            "source": cfg.source if cfg else "—",
            "installed": tool.installed,
            "missing": [m.describe() for m in tool.missing()],
            "hint": next((m.hint for m in tool.missing() if m.hint), ""),
            "surface": (tool.surface.url() if tool.surface else ""),
            "embeddable": bool(tool.surface and tool.surface.embeddable),
            "blockers": [],
        }
        # "Installed" is not "works". A tool that can prove the difference gets
        # asked; one that cannot is taken at its word.
        if row["enabled"] and row["installed"] and tool.health:
            try:
                h = tool.hook("health")
                probe = h() if h else {"ok": True}
                if not probe.get("ok", True):
                    row["blockers"].append(probe.get("detail", "health check failed"))
            except Exception as exc:  # noqa: BLE001 — a failed probe is a finding
                row["blockers"].append(f"health probe error: {type(exc).__name__}")

        if tool.dbt and row["enabled"]:
            dbt_root = d / "transform"
            if tool.dbt.needs_manifest and not (dbt_root / "target" / "manifest.json").exists():
                row["blockers"].append("no dbt manifest — run `pf seed`")
            if tool.dbt.needs_baseline and not (
                    dbt_root / tool.dbt.baseline_dir / "manifest.json").exists():
                row["blockers"].append(
                    f"no baseline — run `pf tool {name} baseline`")
        row["ready"] = row["enabled"] and row["installed"] and not row["blockers"]
        rows.append(row)
    return rows


# ------------------------------------------------------------------- ui ----
def stack_layers() -> list[dict[str, Any]]:
    """Stack-table rows contributed by tools, for the UI's layer view."""
    return [dict(t.stack_layer) for t in all_tools().values() if t.stack_layer]
