"""Which tools exist, and how one from outside this repo gets found.

Two sources, in this order:

  1. **Built-ins** — declared in `pf.tools.<name>` and listed in `BUILTIN_MODULES`.
     They ship with the platform and are the reference implementations.
  2. **Entry points** — any installed distribution advertising the `pf.tools`
     group. This is the plug-and-play path: `pip install pf-tool-elementary`
     and it appears in `pf tool list` without a line changing here.

An entry point may resolve to a `Tool`, or to a zero-argument callable returning
one or many. The callable form exists so a third party can decide at import time
what to declare — a tool that wraps two different upstream versions, say —
without needing a branch inside this module.

## Failure is data

A broken third-party tool must not take down `pf`. Discovery collects load
errors into `DiscoveryError` records and keeps going: `pf tool list` shows the
working tools plus a red row for each broken one, which is far more useful than a
traceback from `pf seed` three commands later. The one place errors *are* raised
is `get()` — asking for a specific broken tool by name should fail loudly.

## What discovery does not do

It does not read project config, decide whether a tool is enabled, or run
anything. `pf.tools.config` owns enablement; this module owns existence. Keeping
them apart is what lets the UI list every available tool while a project enables
two of them.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from importlib import import_module
from importlib.metadata import entry_points
from typing import Any

from pf.capabilities import Capability
from pf.tools.spec import InvalidTool, Tool

ENTRY_POINT_GROUP = "pf.tools"

#: Built-in tools. A module here must be importable *without* the tool's own
#: dependencies installed — the Tool object is declarative and its hooks are
#: dotted strings, so nothing heavy is needed to describe it.
BUILTIN_MODULES: tuple[str, ...] = (
    "pf.tools.openmetadata",
    "pf.tools.recce",
    "pf.tools.wren",
)


@dataclass(frozen=True)
class DiscoveryError:
    """A tool that could not be loaded. Rendered, not raised."""

    source: str
    error: str

    def __str__(self) -> str:
        return f"{self.source}: {self.error}"


def _coerce(obj: Any, source: str) -> list[Tool]:
    """Accept a Tool, a callable returning Tool(s), or an iterable of Tools."""
    if isinstance(obj, Tool):
        return [obj]
    if callable(obj):
        return _coerce(obj(), source)
    if isinstance(obj, Iterable):
        out = []
        for item in obj:
            if not isinstance(item, Tool):
                raise InvalidTool(f"{source} yielded {type(item).__name__}, expected Tool")
            out.append(item)
        return out
    raise InvalidTool(f"{source} resolved to {type(obj).__name__}, expected Tool")


def discover() -> tuple[dict[str, Tool], list[DiscoveryError]]:
    """Every declared tool, plus whatever failed to declare itself."""
    found: dict[str, Tool] = {}
    errors: list[DiscoveryError] = []

    def add(tools: list[Tool], source: str) -> None:
        for t in tools:
            if t.name in found:
                errors.append(DiscoveryError(
                    source, f"tool '{t.name}' already registered by another source"))
                continue
            found[t.name] = t

    for mod_name in BUILTIN_MODULES:
        try:
            mod = import_module(mod_name)
            add(_coerce(mod.TOOL, mod_name), mod_name)
        except Exception as exc:  # noqa: BLE001 — a broken built-in is still data
            errors.append(DiscoveryError(mod_name, f"{type(exc).__name__}: {exc}"))

    for ep in _entry_points():
        try:
            add(_coerce(ep.load(), f"{ep.value}"), f"entry_point:{ep.name}")
        except Exception as exc:  # noqa: BLE001 — third-party code, contained here
            errors.append(DiscoveryError(f"entry_point:{ep.name}",
                                         f"{type(exc).__name__}: {exc}"))
    return found, errors


def _entry_points() -> list[Any]:
    try:
        return list(entry_points(group=ENTRY_POINT_GROUP))
    except TypeError:  # pragma: no cover — Python <3.10 selection API
        return list(entry_points().get(ENTRY_POINT_GROUP, []))  # type: ignore[attr-defined]


def all_tools() -> dict[str, Tool]:
    """Name -> Tool for everything that loaded. Errors are dropped; see discover()."""
    return discover()[0]


def get(name: str) -> Tool:
    """One tool by name. Raises if it does not exist or failed to load."""
    found, errors = discover()
    if name in found:
        return found[name]
    for e in errors:
        if name in e.source or name in e.error:
            raise InvalidTool(f"tool '{name}' failed to load — {e.error}")
    raise InvalidTool(
        f"unknown tool '{name}'. Available: {', '.join(sorted(found)) or '(none)'}")


def for_scope(scope: str) -> dict[str, Tool]:
    """Tools that can be enabled at `project` or `group` level."""
    return {n: t for n, t in all_tools().items() if t.supports(scope)}


# ------------------------------------------------------------ capabilities --
def tool_capabilities() -> dict[str, Capability]:
    """Every tool's scaffold-time capability, keyed by tool name.

    Merged into `pf.capabilities.CAPABILITIES` at import so `pf new-project
    --with recce` and `pf capability-add` keep working unchanged. A tool is
    therefore a capability *plus* runtime hooks, rather than a second, parallel
    way to put files into a project — one scaffolder, one gate merge, one set of
    rules about what may be written.
    """
    return {name: t.capability for name, t in all_tools().items()
            if t.capability is not None}


def register_capabilities(target: dict[str, Capability] | None = None) -> list[str]:
    """Merge tool capabilities into the capability registry. Idempotent.

    Returns the names added. A tool whose capability name collides with a
    hand-written capability is skipped rather than overwriting it: the
    hand-written one is the older, more depended-upon definition, and silently
    replacing it is how a scaffold starts writing different files than it did
    yesterday.
    """
    from pf import capabilities as caps_mod

    target = caps_mod.CAPABILITIES if target is None else target
    added: list[str] = []
    for name, cap in tool_capabilities().items():
        if name in target:
            continue
        target[name] = cap
        added.append(name)
    return added
