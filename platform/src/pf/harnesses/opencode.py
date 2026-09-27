"""OpenCode — `AGENTS.md` through `opencode.json`."""

from __future__ import annotations

from typing import Any

from pf.harness import SKILLS_CELL, Harness, Server, json_text
from pf.harnesses.base import Ctx, Spec


def render_opencode(svs: list[Server]) -> str:
    """`.opencode/opencode.json`: the protocol as its instruction, our servers
    as local MCP. Nothing else — OpenCode's plugin and agent lists are its
    own affair and an empty list here is a list nobody has to reconcile."""
    mcp: dict[str, Any] = {}
    for s in svs:
        s = s.with_project(None)
        spec: dict[str, Any] = {"type": "local", "command": [s.command, *s.args], "enabled": True}
        if s.env:
            spec["environment"] = dict(s.env)
        mcp[s.name] = spec
    return json_text(
        {
            "$schema": "https://opencode.ai/config.json",
            "instructions": ["AGENTS.md"],
            "mcp": mcp,
        }
    )


def _render(ctx: Ctx) -> dict[str, str]:
    return {".opencode/opencode.json": render_opencode(ctx.servers)}


SPEC = Spec(
    key="opencode",
    label="OpenCode",
    order=50,
    rows=(
        Harness(
            "OpenCode",
            "`AGENTS.md` via `opencode.json`",
            "`.opencode/opencode.json`",
            "none — commit gate only",
            "pre-commit",
            "none",
            "rule",
            "rule",
            SKILLS_CELL,
        ),
    ),
    render=_render,
    owner="OpenCode",
)
