"""Cursor — `AGENTS.md` plus an always-applied rule; MCP, hooks and agents in `.cursor/`.

    .cursor/hooks.json               sessionStart, preToolUse (Write, Edit, Delete,
                                     Shell, Read), postToolUse, stop →
                                     `agent_hook.py cursor <event>`
    .cursor/mcp.json                 the MCP servers
    .cursor/rules/data-platform.mdc  where the rules are, always applied
    .cursor/agents/*.md              the power-tools reviewers, `readonly: true`

`preToolUse` can refuse, so the gate runs before the action — one event for
all four tool kinds, so nothing is recorded twice. The Cursor CLI also runs
`.claude/settings.json` hooks; `pf.harness_adapters` answers those as nothing
when Cursor is the caller.
"""

from __future__ import annotations

import json
from typing import Any

from pf.agenthook import BASH, EDIT, READ, WRITE, Verdict
from pf.harness import SKILLS_CELL, Harness, Server, claude_shape, hook_command, json_text
from pf.harness_adapters import Adapter, Out, claude_parse, generic_ok
from pf.harness_assets import Doc, frontmatter, generated_note, readonly
from pf.harnesses.base import Ctx, Spec

#: Kept for callers that still name the first Cursor adapter; it now forwards
#: to `agent_hook.py cursor`.
CURSOR_HOOK = "platform/hooks/cursor_hook.py"


def render_cursor_mcp(svs: list[Server]) -> str:
    """`.cursor/mcp.json`: Claude's shape, `${workspaceFolder}` for the root."""
    return json_text({"mcpServers": claude_shape(svs, "${workspaceFolder}")})


def render_cursor_hooks() -> str:
    """`.cursor/hooks.json`. `sessionStart` also sets `PF_AGENT` for the
    session's shells, so memory notes are attributed."""

    def cmd(ev: str) -> str:
        return hook_command("cursor", ev)

    return json_text(
        {
            "version": 1,
            "hooks": {
                "sessionStart": [{"command": cmd("session"), "timeout": 30}],
                "preToolUse": [{"command": cmd("pre"), "matcher": "Write|Edit|Delete|Shell|Read", "timeout": 60}],
                "postToolUse": [{"command": cmd("post"), "matcher": "Write|Edit|Delete|Shell", "timeout": 60}],
                "stop": [{"command": cmd("stop"), "timeout": 30}],
            },
        }
    )


def render_cursor_rule() -> str:
    """`.cursor/rules/data-platform.mdc`: a pointer, always applied. The rules
    are in `AGENTS.md`; this only says where, and which scope Cursor is in."""
    return (
        "---\n"
        'description: "Data platform protocol: where the rules are and which scope you are in"\n'
        "alwaysApply: true\n"
        "---\n"
        "# Data platform — read these, in order\n"
        "\n"
        "1. `CLAUDE.md` — the router: the directories, what is shared, what is read-only.\n"
        "2. `AGENTS.md` — the protocol. §0 names your scope; the rest is per scope.\n"
        "3. `.memory/MEMORY.md` — what earlier agents learned. `uv run pf memory show` from\n"
        "   where you are working prints the notes that apply there.\n"
        "\n"
        "You are the **Session** scope: a person is in the loop and you have a shell.\n"
        "Ask the graph before reading files — `kg_search`, `kg_neighbors`, `impact_analysis`\n"
        "are MCP tools from `.cursor/mcp.json`. Stay inside one project; never read a sister.\n"
        "\n"
        "`.cursor/hooks.json` runs the same gate Claude Code runs, before every write, delete,\n"
        "shell command and read (`docs/HARNESSES.md`). A refusal is a finding: report it; never\n"
        "retry it another way. Leave a note before you finish (`AGENTS.md` §5).\n"
    )


def render_agent(doc: Doc) -> str:
    fields: dict[str, Any] = {"name": doc.name, "description": doc.description}
    if readonly(doc):
        fields["readonly"] = True
    return frontmatter(fields) + generated_note(doc) + doc.body


def _deny(v: Verdict) -> Out:
    body = json.dumps({"permission": "deny", "user_message": v.message, "agent_message": v.message})
    return body, v.message, 2


def _render(ctx: Ctx) -> dict[str, str]:
    return {
        ".cursor/mcp.json": render_cursor_mcp(ctx.servers),
        ".cursor/hooks.json": render_cursor_hooks(),
        ".cursor/rules/data-platform.mdc": render_cursor_rule(),
    }


SPEC = Spec(
    key="cursor",
    label="Cursor",
    order=20,
    rows=(
        Harness(
            "Cursor",
            "`AGENTS.md` + `.cursor/rules/`",
            "`.cursor/mcp.json`",
            "hook",
            "pre-commit",
            "hooks write stages 01–03",
            "injected on turn one",
            "sessionStart hook",
            SKILLS_CELL,
            "`.cursor/agents/`",
            ".cursor/hooks.json",
            "cursor",
        ),
    ),
    render=_render,
    owner="Cursor",
    adapter=Adapter(
        parse=claude_parse("cursor"),
        deny=_deny,
        allow=lambda v: (json.dumps({"additional_context": v.message}) if v.message else "", "", 0),
        ask=lambda v: (json.dumps({"permission": "ask", "user_message": v.message, "agent_message": v.message}), "", 0),
        context=lambda ev, text: (json.dumps({"additional_context": text, "env": {"PF_AGENT": "cursor"}}), "", 0),
        ok=generic_ok,
    ),
    tools={"Write": WRITE, "Edit": EDIT, "Delete": EDIT, "Shell": BASH, "Read": READ},
    defer_advice=True,
    agents={".cursor/agents/{}.md": render_agent},
    caveats=(
        "- **Cursor** cloud agents do not run `sessionStart`: they are gated but get no",
        "  turn-one context.",
    ),
    launch="cursor",
)
