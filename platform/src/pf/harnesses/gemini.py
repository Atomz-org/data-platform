"""Gemini CLI — `GEMINI.md` imports `AGENTS.md`; `.gemini/settings.json` for the rest."""

from __future__ import annotations

from pf.harness import SKILLS_CELL, Harness, Server, claude_shape, json_text
from pf.harnesses.base import Ctx, Spec


def render_gemini(svs: list[Server]) -> str:
    """`.gemini/settings.json`: Claude's shape; Gemini runs servers from the project."""
    return json_text({"mcpServers": claude_shape(svs, None)})


def _render(ctx: Ctx) -> dict[str, str]:
    return {".gemini/settings.json": render_gemini(ctx.servers)}


SPEC = Spec(
    key="gemini",
    label="Gemini CLI",
    order=40,
    rows=(
        Harness(
            "Gemini CLI",
            "`GEMINI.md`",
            "`.gemini/settings.json`",
            "none — commit gate only",
            "pre-commit",
            "none",
            "rule",
            "rule",
            SKILLS_CELL,
        ),
    ),
    render=_render,
    owner="Gemini CLI",
)
