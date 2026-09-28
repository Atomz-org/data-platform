"""What a harness module declares."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pf.harness import Harness, Server
    from pf.harness_adapters import Adapter
    from pf.harness_assets import Doc


@dataclass(frozen=True)
class Ctx:
    """The shared sources every renderer reads: the MCP servers from
    `.mcp.json` (+ the plugin's), and the `Bash(...)` prefixes of
    `.claude/settings.json`'s `ask` list."""

    root: Path
    servers: list[Server]
    asks: list[str]


@dataclass(frozen=True)
class Spec:
    key: str  # what `agent_hook.py <key> <event>` is called with
    label: str  # what a person reads: notifications, docs
    order: int  # its place in the scorecard
    rows: tuple[Harness, ...]
    #: Every generated text file for this harness, from the shared sources.
    render: Callable[[Ctx], dict[str, str]]
    owner: str  # the generated-config table's first column
    #: The dialect, once the harness's hooks call the core. None: rules only.
    adapter: Adapter | None = None
    tools: Mapping[str, str] = field(default_factory=dict)
    session_event: str = "SessionStart"
    #: The pre-tool answer cannot carry advice without claiming a decision,
    #: so a blast radius found before the call is handed back after it.
    defer_advice: bool = False
    #: No post-tool event: gated, but no provenance (nothing closes an INTENT).
    no_post: bool = False
    #: Subagents: output path pattern (`{}` = agent name) → renderer.
    agents: Mapping[str, Callable[[Doc], str]] = field(default_factory=dict)
    #: Where this harness only half honours its config — said on the scorecard.
    caveats: tuple[str, ...] = ()
    #: Local model providers this module contributes to a harness that can
    #: drive one (read by the OpenCode renderer).
    providers: Mapping[str, dict[str, Any]] = field(default_factory=dict)
    #: `bin/agent-here <launch>` starts it; empty when the launcher does not.
    launch: str = ""
    #: Further launcher lines worth printing on the scorecard.
    sessions: tuple[str, ...] = ()
