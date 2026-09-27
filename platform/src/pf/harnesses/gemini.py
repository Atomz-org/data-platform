"""Gemini CLI — `GEMINI.md` imports `AGENTS.md`; `.gemini/` for the rest.

    .gemini/settings.json   the MCP servers, and the hooks: BeforeTool (the gate,
                            before write_file / replace / run_shell_command /
                            read_file), AfterTool (provenance, formatter),
                            SessionStart (turn-one context), AfterAgent (capture)
    .gemini/agents/*.md     the power-tools reviewers as local subagents

Gemini's hooks answer allow or deny — nothing asks a person — and its
workspace policy tier is documented as inert, so an `ask` rule (`git push`)
is refused with a note to have the person run it.
"""

from __future__ import annotations

from typing import Any

from pf.agenthook import BASH, EDIT, READ, WRITE
from pf.harness import SKILLS_CELL, Harness, Server, claude_shape, hook_command, json_text
from pf.harness_adapters import Adapter, ask_as_deny, claude_parse, exit2, generic_ok, hook_specific
from pf.harness_assets import Doc, frontmatter, generated_note, readonly_line
from pf.harnesses.base import Ctx, Spec

WRITES = "write_file|replace|run_shell_command"


def render_gemini(svs: list[Server]) -> str:
    """`.gemini/settings.json`: Claude's server shape, and the hooks.

    `$GEMINI_PROJECT_DIR` is the root Gemini exports to its hooks. Timeouts are
    milliseconds here, unlike everywhere else.
    """
    root = '"$GEMINI_PROJECT_DIR"'

    def h(event: str, name: str, matcher: str | None = None) -> list[dict[str, Any]]:
        entry: dict[str, Any] = {
            "hooks": [
                {"name": name, "type": "command", "command": hook_command("gemini", event, root), "timeout": 60000}
            ]
        }
        return [{"matcher": matcher, **entry}] if matcher else [entry]

    return json_text(
        {
            "mcpServers": claude_shape(svs, None),
            "hooks": {
                "BeforeTool": h("pre", "pf-gate", WRITES + "|read_file|read_many_files"),
                "AfterTool": h("post", "pf-provenance", WRITES),
                "SessionStart": h("session", "pf-context"),
                "AfterAgent": h("stop", "pf-capture"),
            },
        }
    )


def render_agent(doc: Doc) -> str:
    """`.gemini/agents/<name>.md`. Gemini's `tools:` names are not stable
    enough to pin, so read-only is stated rather than configured — and the
    gate still refuses what matters."""
    fields: dict[str, Any] = {"name": doc.name, "description": doc.description, "kind": "local"}
    if isinstance(doc.meta.get("maxTurns"), int):
        fields["max_turns"] = doc.meta["maxTurns"]
    return frontmatter(fields) + generated_note(doc) + readonly_line(doc) + doc.body


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
            "hook — ask is refused",
            "pre-commit",
            "hooks write stages 01–03",
            "injected on turn one",
            "SessionStart hook",
            SKILLS_CELL,
            "`.gemini/agents/`",
            ".gemini/settings.json",
            "gemini",
        ),
    ),
    render=_render,
    owner="Gemini CLI",
    adapter=Adapter(
        parse=claude_parse("gemini"),
        deny=exit2,
        allow=lambda v: hook_specific("AfterTool", v.message),
        ask=ask_as_deny,
        context=hook_specific,
        ok=generic_ok,
    ),
    tools={
        "write_file": WRITE,
        "replace": EDIT,
        "run_shell_command": BASH,
        "read_file": READ,
        "read_many_files": READ,
    },
    defer_advice=True,
    agents={".gemini/agents/{}.md": render_agent},
    caveats=(
        "- **Gemini CLI** cannot ask a person from a hook, so an `ask` rule (`git push`)",
        "  is refused there with a note to have the person run it.",
    ),
    launch="gemini",
)
