"""Cursor — `AGENTS.md` plus an always-applied rule, MCP and hooks in `.cursor/`."""

from __future__ import annotations

from pf.harness import SKILLS_CELL, Harness, Server, claude_shape, json_text
from pf.harnesses.base import Ctx, Spec

#: The Cursor adapter. One script, two events; see `platform/hooks/cursor_hook.py`.
CURSOR_HOOK = "platform/hooks/cursor_hook.py"


def render_cursor_mcp(svs: list[Server]) -> str:
    """`.cursor/mcp.json`: Claude's shape, `${workspaceFolder}` for the root."""
    return json_text({"mcpServers": claude_shape(svs, "${workspaceFolder}")})


def render_cursor_hooks() -> str:
    """`.cursor/hooks.json`: two events, one adapter, our gate.

    `beforeShellExecution` can block, so the `--no-verify` guard lives there:
    a commit that skips the pre-commit hook skips the only gate Cursor has.
    `afterFileEdit` cannot block — Cursor has no pre-edit event — so the gate
    runs after the fact and reports; the commit gate still refuses the file.
    """
    return json_text(
        {
            "version": 1,
            "hooks": {
                "beforeShellExecution": [
                    {
                        "command": f"uv run python {CURSOR_HOOK} shell",
                        "description": "gate.yaml cannot be bypassed: block --no-verify",
                    }
                ],
                "afterFileEdit": [
                    {
                        "command": f"uv run python {CURSOR_HOOK} edit",
                        "description": "gate.yaml verdict for the edited file (advisory — Cursor has no pre-edit hook)",
                    }
                ],
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
        "Enforcement here is narrower than in Claude Code, and `docs/HARNESSES.md` says how:\n"
        "the shell hook blocks `--no-verify`; edits are judged after the fact and again at\n"
        "commit by `gate.yaml`. Run `uv run pf gate --paths <files>` before you commit.\n"
        "Leave a note before you finish (`AGENTS.md` §5).\n"
    )


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
            "partial — shell: `--no-verify` blocked; edits: verdict after the fact",
            "pre-commit",
            "none",
            "rule",
            "rule",
            SKILLS_CELL,
        ),
    ),
    render=_render,
    owner="Cursor",
    caveats=(
        "**Cursor** — `beforeShellExecution` can block and `afterFileEdit` cannot, so",
        "  `platform/hooks/cursor_hook.py` blocks `--no-verify` before it runs and reports",
        "  `gate.yaml`'s verdict on an edit after the edit has happened.",
    ),
)
