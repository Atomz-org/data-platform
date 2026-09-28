"""GitHub Copilot — the CLI, VS Code agent mode and the cloud coding agent.

    .github/hooks/pf.json        one file all three read: SessionStart,
                                 PreToolUse, PostToolUse, Stop →
                                 `agent_hook.py copilot <event>`
    .github/agents/*.agent.md    the power-tools reviewers, tools: read, search,
                                 execute (no edit) when read-only
    .vscode/mcp.json             the MCP servers, for VS Code

PascalCase event names are accepted by all three and get a snake_case
payload; camelCase (`toolName`, `toolArgs` as a JSON string) is also read,
whichever arrives. VS Code ignores matchers, so the adapter filters by tool.
The cloud agent reads `.github/hooks/` from the default branch only.
"""

from __future__ import annotations

import json
from typing import Any

from pf.agenthook import BASH, EDIT, READ, WRITE, Call
from pf.harness import SKILLS_CELL, Harness, Server, hook_command, json_text
from pf.harness_adapters import Adapter, Out, call, claude_parse, first, generic_ok, obj
from pf.harness_assets import Doc, frontmatter, generated_note, readonly
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


def render_hooks() -> str:
    """`.github/hooks/pf.json`. `command` is VS Code's key and `bash` the
    CLI's; both are given, as are both timeout spellings."""

    def one(event: str) -> list[dict[str, Any]]:
        c = hook_command("copilot", event)
        return [{"type": "command", "command": c, "bash": c, "timeout": 60, "timeoutSec": 60}]

    return json_text(
        {
            "version": 1,
            "hooks": {
                "SessionStart": one("session"),
                "PreToolUse": one("pre"),
                "PostToolUse": one("post"),
                "Stop": one("stop"),
            },
        }
    )


def render_agent(doc: Doc) -> str:
    fields: dict[str, Any] = {"name": doc.name, "description": doc.description}
    if readonly(doc):
        fields["tools"] = ["read", "search", "execute"]
    return frontmatter(fields) + generated_note(doc) + doc.body


def parse(p: dict[str, Any]) -> Call:
    if "tool_name" in p:
        return claude_parse("copilot")(p)
    return call("copilot", p, first(p, "toolName"), obj(p.get("toolArgs")), first(p, "toolCallId", "toolUseId"))


def decision(verdict: str, reason: str) -> str:
    """The CLI reads a top-level `permissionDecision`; VS Code reads it under
    `hookSpecificOutput`. One file serves both, so the answer carries both."""
    return json.dumps(
        {
            "permissionDecision": verdict,
            "permissionDecisionReason": reason,
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": verdict,
                "permissionDecisionReason": reason,
            },
        }
    )


def _context(event: str, text: str) -> Out:
    if not text:
        return "", "", 0
    return (
        json.dumps(
            {"additionalContext": text, "hookSpecificOutput": {"hookEventName": event, "additionalContext": text}}
        ),
        "",
        0,
    )


def _render(ctx: Ctx) -> dict[str, str]:
    return {".vscode/mcp.json": render_vscode(ctx.servers), ".github/hooks/pf.json": render_hooks()}


SPEC = Spec(
    key="copilot",
    label="Copilot",
    order=30,
    rows=(
        Harness(
            "Copilot — CLI and VS Code",
            "`.github/copilot-instructions.md`",
            "`.vscode/mcp.json`",
            "hook (VS Code: Preview)",
            "pre-commit",
            "hooks write stages 01–03",
            "injected on turn one",
            "SessionStart hook",
            SKILLS_CELL,
            "`.github/agents/`",
            ".github/hooks/pf.json",
            "copilot",
        ),
        Harness(
            "Copilot — coding agent",
            "`.github/copilot-instructions.md` + `copilot-setup-steps.yml`",
            "repository settings, not a file",
            "hook — default branch only",
            "pre-commit, if installed in the runner",
            "hooks write stages 01–03",
            "injected on turn one",
            "SessionStart hook",
            SKILLS_CELL,
            "`.github/agents/`",
            ".github/hooks/pf.json",
            "copilot",
        ),
    ),
    render=_render,
    owner="Copilot (CLI, VS Code, coding agent)",
    adapter=Adapter(
        parse=parse,
        deny=lambda v: (decision("deny", v.message), v.message, 2),
        allow=lambda v: _context("PostToolUse", v.message),
        ask=lambda v: (decision("ask", v.message), "", 0),
        context=_context,
        ok=generic_ok,
    ),
    tools={
        # The CLI's names …
        "edit": EDIT,
        "create": WRITE,
        "bash": BASH,
        "powershell": BASH,
        "view": READ,
        # … and VS Code's tool ids.
        "create_file": WRITE,
        "replace_string_in_file": EDIT,
        "multi_replace_string_in_file": EDIT,
        "insert_edit_into_file": EDIT,
        "apply_patch": EDIT,
        "edit_notebook_file": EDIT,
        "run_in_terminal": BASH,
        "read_file": READ,
    },
    defer_advice=True,
    agents={".github/agents/{}.agent.md": render_agent},
    caveats=(
        "- **Copilot coding agent** reads `.github/hooks/` from the default branch: a",
        "  hook change reaches it after the merge, not on the branch that makes it.",
        "- **Copilot in VS Code** runs hooks as a Preview feature (`chat.useHooks`).",
    ),
    launch="copilot",
)
