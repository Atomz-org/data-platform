"""GitHub Copilot — VS Code chat and the cloud coding agent."""

from __future__ import annotations

from typing import Any

from pf.harness import SKILLS_CELL, Harness, Server, json_text
from pf.harnesses.base import Ctx, Spec


def render_vscode(svs: list[Server]) -> str:
    """`.vscode/mcp.json`: VS Code's `servers:` with an explicit transport, for
    Copilot in agent mode."""
    out: dict[str, Any] = {}
    for s in svs:
        s = s.with_project("${workspaceFolder}")
        spec: dict[str, Any] = {"type": "stdio", "command": s.command, "args": list(s.args)}
        if s.env:
            spec["env"] = dict(s.env)
        out[s.name] = spec
    return json_text({"servers": out})


def _render(ctx: Ctx) -> dict[str, str]:
    return {".vscode/mcp.json": render_vscode(ctx.servers)}


SPEC = Spec(
    key="copilot",
    label="Copilot",
    order=30,
    rows=(
        Harness(
            "Copilot — VS Code chat",
            "`.github/copilot-instructions.md`",
            "`.vscode/mcp.json`",
            "none — commit gate only",
            "pre-commit",
            "none",
            "rule",
            "rule",
            SKILLS_CELL,
        ),
        Harness(
            "Copilot — coding agent",
            "`.github/copilot-instructions.md` + `copilot-setup-steps.yml`",
            "repository settings, not a file",
            "none — `pf gate` in `AGENTS.md` §4",
            "pre-commit, if installed in the runner",
            "none",
            "rule",
            "rule",
            SKILLS_CELL,
        ),
    ),
    render=_render,
    owner="Copilot (VS Code)",
)
