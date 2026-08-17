"""The tool contract — what a pluggable tool declares, and what it may not do.

`pf.capabilities` already solved half of this: a capability is a declarative
bundle of files, settings and gate rules that reaches a project at scaffold time.
It stops there on purpose, and the reason is written into its docstring — a
capability that could run arbitrary code at scaffold time would be a plugin
system, and a plugin system inside the thing that enforces the safety gate is a
way around the safety gate.

But a real tool is not only files. Recce, Elementary, a lineage service, a
freshness monitor — each also wants to *run*: contribute a Dagster asset, serve a
UI, produce an artefact from the dbt manifest. Evidence BI is the proof. Wiring
it in touched seven places: `capabilities.py`, a bootstrap step, a CLI sub-app, a
projection module, a toolkit, the UI's stack table, and the gate. The eighth tool
would touch seven more, and that is exactly the sideways growth the capability
seam was built to prevent.

A `Tool` is the missing half. It pairs the declarative capability with runtime
hooks, and every consumer — scaffolder, bootstrap, Dagster factory, CLI, UI —
reads the registry instead of naming tools individually. Adding a tool is one
`Tool` object. Adding one from *outside* this repo is a `pf.tools` entry point in
any installed package; nothing here changes.

## The safety boundary

The gate concern is preserved, precisely rather than by avoidance:

  * **Declarative where it can bite.** Files, settings and gate rules still come
    from a `Capability`. A tool cannot compute them.
  * **Tightening only.** `Tool.gate_sections()` rejects any contribution to a
    section that would *loosen* the gate (`denylist_except`, `autoMergeAllowlist`,
    `maxFiles`, `blockOn`). A tool may forbid more; it can never permit more.
    This is checked at construction, so an unsafe tool fails loudly at import
    rather than silently widening the policy that judges it.
  * **Lazily resolved code.** Runtime hooks are dotted `"module:function"`
    strings, not callables. Listing tools, rendering the UI and running the gate
    never import a tool's implementation — only enabling one does. That keeps
    `pf tool list` working when the tool's dependencies are absent, and keeps
    third-party code out of the process that decides whether third-party code
    may write a file.
"""

from __future__ import annotations

import importlib
import os
import shutil
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from pf.capabilities import Capability

Scope = Literal["project", "group"]

# Gate sections a tool may add to. Everything else in gate.yaml either loosens
# the policy (`denylist_except`, `autoMergeAllowlist`) or is a scalar budget
# (`maxFiles`, `blockOn`) that a tool overwriting would silently raise.
TIGHTENING_SECTIONS = frozenset({"denylist", "platform_denylist", "impact_required"})


class InvalidTool(ValueError):
    """A tool declaration that would be unsafe or unusable. Raised at import."""


# ------------------------------------------------------------ requirements --
@dataclass(frozen=True)
class Requirement:
    """Something that must be present before a tool can run.

    Declared rather than discovered so `pf tool doctor` can explain a missing
    piece *before* a Dagster run fails halfway through, and so a tool whose
    binary is absent degrades to "not installed" instead of an ImportError in
    the middle of the asset graph.
    """

    kind: Literal["python", "binary", "env"]
    name: str
    hint: str = ""

    def satisfied(self) -> bool:
        if self.kind == "binary":
            return shutil.which(self.name) is not None
        if self.kind == "env":
            return bool(os.environ.get(self.name))
        try:
            importlib.import_module(self.name)
            return True
        except Exception:  # noqa: BLE001 — a broken import is an unmet requirement
            return False

    def describe(self) -> str:
        return f"{self.kind}:{self.name}"


# --------------------------------------------------------------------- dbt --
@dataclass(frozen=True)
class DbtBinding:
    """How a tool attaches to the dbt project.

    Every tool worth adding here reads dbt's artefacts, so the binding is a
    first-class field rather than something each tool rediscovers. `pf tool
    doctor` uses it to say "manifest.json missing — run `pf seed`" instead of
    letting the tool fail with its own, less actionable error.
    """

    #: Needs `target/manifest.json` — i.e. the project must have been parsed.
    needs_manifest: bool = False
    #: Needs a *second*, earlier set of dbt artefacts to compare against. This is
    #: what makes a diff tool different from a lint tool: it is only meaningful
    #: relative to a baseline, and having no baseline is a distinct state from
    #: having no manifest — worth its own message rather than one "not ready".
    needs_baseline: bool = False
    #: Directory (relative to the dbt project) holding those baseline artefacts.
    baseline_dir: str = "target-base"
    #: Config file the tool reads, relative to the dbt project directory.
    config_file: str = ""
    #: Paths the tool writes, relative to the project.
    artefacts: tuple[str, ...] = ()


# ------------------------------------------------------------------ surface --
@dataclass(frozen=True)
class Surface:
    """A web UI the tool serves.

    `embeddable` is load-bearing. A tool that sends `X-Frame-Options: DENY`
    cannot be iframed into the control plane however much we would like it to be,
    and the honest response is a deep link rather than a blank rectangle the
    operator is left to debug.
    """

    port: int
    path: str = "/"
    embeddable: bool = True
    #: argv to start the server. `{token}` placeholders are rendered against the
    #: project context (project_dir, dbt_dir, port, state_file, ...).
    start: tuple[str, ...] = ()
    health: str = "/"

    def url(self, host: str = "127.0.0.1") -> str:
        return f"http://{host}:{self.port}{self.path}"


# --------------------------------------------------------------------- tool --
@dataclass(frozen=True)
class Tool:
    """One pluggable tool.

    Hooks are dotted `"pf.tools.recce:dagster_assets"` strings. See the module
    docstring for why they are not callables.
    """

    name: str
    title: str
    summary: str
    url: str = ""
    #: Where the tool can be enabled. A tool scoped to both is enabled at the
    #: group and inherited by every sister, which is how one decision reaches a
    #: family of companies instead of being repeated per project.
    scope: frozenset[str] = frozenset({"project"})
    capability: Capability | None = None
    #: Whether a newly scaffolded group turns this on. A default, not a
    #: requirement — `tools.yaml` is written once and then owned by the group,
    #: so this only decides what a new family starts with. It exists so that
    #: registering a tool is still the only step: a tool no new group enables is
    #: a tool nobody discovers, and the alternative was a hardcoded list in the
    #: scaffolder that every new tool had to remember to edit.
    default_enabled: bool = False
    #: Whether this tool's `bootstrap` hook runs even when its requirements are
    #: missing. Off by default, because most bootstraps drive the binary.
    #:
    #: It exists for tools whose bootstrap is a pure *projection* — it reads the
    #: project and writes a file, and the client is only needed later to send
    #: that file somewhere. OpenMetadata is the case: skipping its bootstrap on
    #: a laptop with no `metadata` CLI meant a project scaffolded there had no
    #: catalogue artefacts at all, so the integration silently depended on who
    #: ran the scaffolder. A tool setting this must degrade on its own — the
    #: hook is called with the requirement genuinely absent.
    offline_bootstrap: bool = False
    requires: tuple[Requirement, ...] = ()
    dbt: DbtBinding | None = None
    surface: Surface | None = None

    # -- lazily resolved hooks ------------------------------------------------
    #: `(root, group, project, project_dir, config) -> StepResult`. Idempotent:
    #: it runs on every `pf bootstrap`.
    bootstrap: str = ""
    #: `(ToolContext) -> ToolContribution`. Called by the Dagster factory.
    dagster: str = ""
    #: `(typer.Typer) -> None`. Registers tool-specific subcommands.
    commands: str = ""
    #: `() -> {"ok": bool, "detail": str}`. "Installed" and "works" are not the
    #: same claim: a CLI can install cleanly while its compiled engine refuses
    #: every real request. A tool that can tell the difference says so here, and
    #: `readiness()` reports it as a blocker rather than showing a green tick
    #: over something that cannot answer a question.
    health: str = ""

    #: Row for the UI's stack table, so a tool appears in the layer view without
    #: `ui/app.py` growing a hardcoded entry per tool.
    stack_layer: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.replace("-", "_").isidentifier():
            raise InvalidTool(f"tool name {self.name!r} is not a usable slug")
        if not self.scope:
            raise InvalidTool(f"tool {self.name!r} declares no scope")
        bad = set(self.scope) - {"project", "group"}
        if bad:
            raise InvalidTool(f"tool {self.name!r} has unknown scope(s): {sorted(bad)}")
        # The safety check the module docstring promises. Done at construction so
        # an unsafe tool cannot be registered at all, rather than being caught
        # later by whichever consumer happens to look first.
        self.gate_sections()

    def gate_sections(self) -> dict[str, list[str]]:
        """The tool's gate contribution, rejected if it would loosen the gate."""
        if self.capability is None:
            return {}
        loosening = set(self.capability.gate) - TIGHTENING_SECTIONS
        if loosening:
            raise InvalidTool(
                f"tool {self.name!r} contributes to gate section(s) "
                f"{sorted(loosening)}, which would loosen the policy that judges "
                f"it. Tools may only add to: {', '.join(sorted(TIGHTENING_SECTIONS))}.")
        return dict(self.capability.gate)

    # -- requirements ---------------------------------------------------------
    def missing(self) -> list[Requirement]:
        return [r for r in self.requires if not r.satisfied()]

    @property
    def installed(self) -> bool:
        return not self.missing()

    def supports(self, scope: str) -> bool:
        return scope in self.scope

    # -- hooks ----------------------------------------------------------------
    def hook(self, which: str) -> Callable[..., Any] | None:
        """Resolve one hook, or None if the tool does not declare it.

        Import errors are deliberately *not* swallowed: a tool that declares a
        hook it cannot load is broken, and hiding that produces a tool which
        silently does nothing. Check `missing()` first — that is the check which
        is allowed to come back negative.
        """
        ref = getattr(self, which, "")
        if not ref:
            return None
        return load_hook(ref)


def load_hook(ref: str) -> Callable[..., Any]:
    """Resolve `"package.module:attribute"` to the attribute."""
    if ":" not in ref:
        raise InvalidTool(f"hook {ref!r} must be 'module:attribute'")
    mod_name, _, attr = ref.partition(":")
    mod = importlib.import_module(mod_name)
    try:
        return getattr(mod, attr)
    except AttributeError as exc:
        raise InvalidTool(f"hook {ref!r}: {mod_name} has no attribute {attr!r}") from exc


# ------------------------------------------------------------------ context --
@dataclass(frozen=True)
class ToolContext:
    """What a runtime hook is given.

    A frozen record rather than loose arguments so adding a field later does not
    break every tool's signature — including tools that live outside this repo,
    which is the case entry-point discovery exists to serve.
    """

    root: Any            # repo root (Path)
    group: str
    project: str
    project_dir: Any     # Path
    dbt_dir: Any         # Path
    warehouse: Any = None
    config: dict[str, Any] = field(default_factory=dict)

    def render(self, argv: tuple[str, ...]) -> list[str]:
        """Fill `{token}` placeholders in a Surface.start argv."""
        tokens = {
            "root": str(self.root), "group": self.group, "project": self.project,
            "project_dir": str(self.project_dir), "dbt_dir": str(self.dbt_dir),
            **{k: str(v) for k, v in self.config.items()},
        }
        return [a.format(**tokens) if "{" in a else a for a in argv]


# ------------------------------------------------------------ contribution --
@dataclass
class ToolContribution:
    """What a tool adds to a project's Dagster definitions.

    Plain lists and dicts rather than an assembled `Definitions`: the factory
    merges contributions from several tools, and merging Definitions objects
    loses the executor and metadata the platform sets centrally.
    """

    assets: list[Any] = field(default_factory=list)
    asset_checks: list[Any] = field(default_factory=list)
    resources: dict[str, Any] = field(default_factory=dict)
    #: Surfaced on the project's Definitions metadata, so a tool's UI is
    #: reachable from Dagster without the operator knowing which port it chose.
    metadata: dict[str, Any] = field(default_factory=dict)
