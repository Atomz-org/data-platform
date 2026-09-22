"""Harness configs — one source, every agent tool, checked on every PR.

`AGENTS.md` already makes the *rules* agnostic: it is written per execution
scope, not per vendor, and Codex, Cursor, Copilot, Gemini, OpenCode and Claude
all reach it. What was not agnostic was everything a rule cannot do:

    the graph      `kg_search`, `impact_analysis` and the rest reach a tool only
                   through an MCP server, and `.mcp.json` is Claude's format.
                   Codex wants TOML, VS Code wants `servers:`, OpenCode wants a
                   command array. A tool with no server reads files instead of
                   asking the graph — and "ask the graph before reading files"
                   becomes a rule it cannot follow.

    the gate       `gate.yaml` fires through Claude Code's PreToolUse hook and
                   nowhere else. Every other tool's instructions say "run the
                   gate yourself before committing" — a rule an agent must
                   remember is not enforcement.

This module treats the per-harness config layer the way the platform treats
every derived artefact: **generated from one source, committed for review,
and checked for drift by `pf context check`.** The sources are what they were —
`.mcp.json` for the servers, `gate.yaml` for what is blocked, `AGENTS.md` for
the rules — and the targets are rendered from them, never hand-edited.

## What each harness gets, honestly

Enforcement exists where a hook exists. Cursor has shell and post-edit hooks,
so it gets the `--no-verify` guard and an after-the-fact gate verdict. Codex,
Gemini, Copilot and OpenCode have no tool hooks; for them the **commit gate**
(`platform/hooks/pre_commit.sh`, installed by `pf install-hook`) is the
backstop, and the scorecard in `docs/HARNESSES.md` says so in as many words.
A scorecard that claimed parity would be the worst outcome: a tool believing
it is gated when it is not.

## Where this came from

The shape — a compliance table per harness, an adapter that maps a foreign
hook payload onto one shared code path, a Codex TOML with persistent
instructions — is taken from `vendor/ecc` (see the registry). What is *not*
taken is any of its hook bodies: the gate here is ours, and the point of an
adapter is that there is one gate.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: Claude Code's placeholder in `.mcp.json`. Other harnesses do not expand it,
#: so each renderer substitutes what that harness understands.
CLAUDE_TOKEN = "${CLAUDE_PROJECT_DIR}"

#: The Claude-format server files that are the source of truth, in merge
#: order. The plugin's file carries the `pf` server; a harness that does not
#: load Claude plugins still needs it, which is the whole reason the plugin's
#: file is read here rather than left to the plugin.
SOURCES: tuple[str, ...] = (
    ".mcp.json",
    "platform/toolkits/power-tools/.mcp.json",
)

#: Every file this module owns, relative to the repo root. `pf context refresh`
#: writes them; `pf context check` fails when one is missing or differs.
TARGETS: tuple[str, ...] = (
    ".codex/config.toml",
    ".cursor/mcp.json",
    ".cursor/hooks.json",
    ".cursor/rules/data-platform.mdc",
    ".gemini/settings.json",
    ".vscode/mcp.json",
    ".opencode/opencode.json",
    "docs/HARNESSES.md",
)

#: The Cursor adapter. One script, two events; see `platform/hooks/cursor_hook.py`.
CURSOR_HOOK = "platform/hooks/cursor_hook.py"


# ---------------------------------------------------------------- servers --
@dataclass(frozen=True)
class Server:
    name: str
    command: str
    args: tuple[str, ...]
    env: tuple[tuple[str, str], ...]

    def with_project(self, token: str | None) -> Server:
        """Rewrite Claude's placeholder for another harness.

        `token` is what to write instead — `${workspaceFolder}` for the VS Code
        family — or `None` to make paths relative, for harnesses that run the
        server with the repository as its working directory. A bare
        placeholder as an env value becomes `.` rather than an empty string,
        because an empty `PF_PROJECT_DIR` resolves to nothing rather than to
        here.
        """

        def sub(v: str) -> str:
            if token is not None:
                return v.replace(CLAUDE_TOKEN, token)
            if v == CLAUDE_TOKEN:
                return "."
            return v.replace(CLAUDE_TOKEN + "/", "")

        return Server(
            self.name,
            self.command,
            tuple(sub(a) for a in self.args),
            tuple((k, sub(v)) for k, v in self.env),
        )


def servers(root: str | Path) -> list[Server]:
    """The MCP servers, merged from every source file that exists, by name."""
    root = Path(root)
    found: dict[str, Server] = {}
    for rel in SOURCES:
        p = root / rel
        if not p.is_file():
            continue
        raw = json.loads(p.read_text(encoding="utf-8")) or {}
        for name, spec in (raw.get("mcpServers") or {}).items():
            spec = spec or {}
            found[name] = Server(
                name=name,
                command=str(spec.get("command") or ""),
                args=tuple(str(a) for a in (spec.get("args") or [])),
                env=tuple(sorted((str(k), str(v)) for k, v in (spec.get("env") or {}).items())),
            )
    return [found[n] for n in sorted(found)]


# --------------------------------------------------------------- renderers --
def _json(obj: Any) -> str:
    return json.dumps(obj, indent=2, sort_keys=False) + "\n"


def _toml_str(s: str) -> str:
    return json.dumps(s)  # a JSON string literal is a valid TOML basic string


def render_codex(svs: list[Server]) -> str:
    """`.codex/config.toml`: the servers, the protocol, and a sandbox that can write.

    Only our servers. The reference config this shape comes from lists six
    third-party `npx` servers; a data platform's MCP surface is its graph and
    its warehouse tools, and every extra server is context every session pays
    for. `persistent_instructions` is additive to `AGENTS.md`, which Codex reads
    natively — it is the one line that survives a Codex update.
    """
    lines = [
        "#:schema https://developers.openai.com/codex/config-schema.json",
        "# GENERATED by `pf context refresh` from .mcp.json — do not hand-edit.",
        "# Codex has no tool hooks: gate.yaml is enforced at commit by",
        "# platform/hooks/pre_commit.sh (`pf install-hook`), and by you before that",
        "# with `uv run pf gate --paths <files>`. See docs/HARNESSES.md.",
        "",
        'approval_policy = "on-request"',
        'sandbox_mode = "workspace-write"',
        "",
        "persistent_instructions = "
        + _toml_str(
            "Follow AGENTS.md. Section 0 names your scope (Session). Ask the graph "
            "before reading files (kg_search, impact_analysis). Run `uv run pf gate "
            "--paths <files>` before committing; never pass --no-verify."
        ),
        "",
    ]
    for s in svs:
        s = s.with_project(None)
        lines.append(f"[mcp_servers.{s.name}]")
        lines.append(f"command = {_toml_str(s.command)}")
        lines.append("args = [" + ", ".join(_toml_str(a) for a in s.args) + "]")
        if s.env:
            lines.append("env = { " + ", ".join(f"{k} = {_toml_str(v)}" for k, v in s.env) + " }")
        lines.append("startup_timeout_sec = 30")
        lines.append("")
    return "\n".join(lines)


def _claude_shape(svs: list[Server], token: str | None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for s in svs:
        s = s.with_project(token)
        spec: dict[str, Any] = {"command": s.command, "args": list(s.args)}
        if s.env:
            spec["env"] = dict(s.env)
        out[s.name] = spec
    return out


def render_cursor_mcp(svs: list[Server]) -> str:
    """`.cursor/mcp.json`: Claude's shape, `${workspaceFolder}` for the root."""
    return _json({"mcpServers": _claude_shape(svs, "${workspaceFolder}")})


def render_gemini(svs: list[Server]) -> str:
    """`.gemini/settings.json`: Claude's shape; Gemini runs servers from the project."""
    return _json({"mcpServers": _claude_shape(svs, None)})


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
    return _json({"servers": out})


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
    return _json(
        {
            "$schema": "https://opencode.ai/config.json",
            "instructions": ["AGENTS.md"],
            "mcp": mcp,
        }
    )


def render_cursor_hooks() -> str:
    """`.cursor/hooks.json`: two events, one adapter, our gate.

    `beforeShellExecution` can block, so the `--no-verify` guard lives there:
    a commit that skips the pre-commit hook skips the only gate Cursor has.
    `afterFileEdit` cannot block — Cursor has no pre-edit event — so the gate
    runs after the fact and reports; the commit gate still refuses the file.
    """
    return _json(
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


# --------------------------------------------------------------- scorecard --
@dataclass(frozen=True)
class Harness:
    name: str
    entry: str
    graph: str
    pre_tool_gate: str
    commit_gate: str
    provenance: str
    memory: str
    session_context: str


#: What is *true* for each tool, not what would be nice. "rule" means the
#: protocol asks for it and nothing enforces it; that word is the point.
HARNESSES: tuple[Harness, ...] = (
    Harness(
        "Claude Code",
        "`CLAUDE.md` + hooks",
        "`.mcp.json` + power-tools plugin",
        "hook — `pre_tool_use.py` on every Edit/Write",
        "pre-commit",
        "hooks write stages 01–03",
        "injected on turn one",
        "`session_start.sh`",
    ),
    Harness(
        "Codex CLI",
        "`AGENTS.md`, natively",
        "`.codex/config.toml`",
        "none — commit gate only",
        "pre-commit",
        "none",
        "rule — `pf memory show`",
        "rule — `AGENTS.md` §1",
    ),
    Harness(
        "Cursor",
        "`AGENTS.md` + `.cursor/rules/`",
        "`.cursor/mcp.json`",
        "partial — shell: `--no-verify` blocked; edits: verdict after the fact",
        "pre-commit",
        "none",
        "rule",
        "rule",
    ),
    Harness(
        "Copilot — VS Code chat",
        "`.github/copilot-instructions.md`",
        "`.vscode/mcp.json`",
        "none — commit gate only",
        "pre-commit",
        "none",
        "rule",
        "rule",
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
    ),
    Harness(
        "Gemini CLI",
        "`GEMINI.md`",
        "`.gemini/settings.json`",
        "none — commit gate only",
        "pre-commit",
        "none",
        "rule",
        "rule",
    ),
    Harness(
        "OpenCode",
        "`AGENTS.md` via `opencode.json`",
        "`.opencode/opencode.json`",
        "none — commit gate only",
        "pre-commit",
        "none",
        "rule",
        "rule",
    ),
    Harness(
        "Prompt-only (Continue, Ollama, mlx)",
        "paste `AGENTS.md`",
        "none",
        "none",
        "pre-commit",
        "none",
        "rule",
        "rule",
    ),
)


def render_scorecard() -> str:
    """`docs/HARNESSES.md`: per harness, what is enforced and what is asked."""
    lines = [
        "# Harnesses — what each agent tool actually gets",
        "",
        "GENERATED by `pf context refresh` from `platform/src/pf/harness.py`. Do not",
        "hand-edit; `pf context check` fails when this file and the code disagree.",
        "",
        "The rules are written once, per execution scope, in `AGENTS.md`, and every",
        "tool reaches them. What differs by tool is **enforcement**: a hook can stop an",
        "action; a rule can only ask. This table says which is which. Where it says",
        "*rule*, nothing checks — and the commit gate (`platform/hooks/pre_commit.sh`,",
        "`pf install-hook`) is the backstop every tool shares.",
        "",
        "| Harness | Entry point | Graph (MCP) | Pre-tool gate | Commit gate | Provenance | Memory | Session context |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for h in HARNESSES:
        lines.append(
            f"| {h.name} | {h.entry} | {h.graph} | {h.pre_tool_gate} | {h.commit_gate} "
            f"| {h.provenance} | {h.memory} | {h.session_context} |"
        )
    lines += [
        "",
        "## The generated configs",
        "",
        "One source, `.mcp.json` (+ the power-tools plugin's `.mcp.json` for the `pf`",
        "server), rendered into each harness's format. Change the source; regenerate.",
        "",
        "| Harness | File | Regenerate with |",
        "|---|---|---|",
    ]
    for t in TARGETS:
        if t == "docs/HARNESSES.md":
            continue
        lines.append(f"| {_owner(t)} | `{t}` | `pf context refresh` |")
    lines += [
        "",
        "## Verify",
        "",
        "```bash",
        "uv run pf context check              # every config above is current",
        "ls .git/hooks/pre-commit             # the commit gate is installed (pf install-hook)",
        "uv run pf gate --paths <file,...>    # the gate, by hand, from any tool",
        "```",
        "",
        "## Why Cursor is 'partial' and the others are 'none'",
        "",
        "Cursor exposes `beforeShellExecution` (can block) and `afterFileEdit` (cannot).",
        "So `platform/hooks/cursor_hook.py` blocks `--no-verify` before it runs — the",
        "commit gate is the only gate Cursor has, and that flag skips it — and reports",
        "`gate.yaml`'s verdict on an edit after the edit has happened. Codex, Gemini,",
        "Copilot and OpenCode expose no tool hooks at all. Claiming more than this",
        "would leave a tool believing it is gated when it is not, which is the one",
        "outcome worse than an ungated tool that knows it.",
        "",
    ]
    return "\n".join(lines)


def _owner(target: str) -> str:
    return {
        ".codex/config.toml": "Codex CLI",
        ".cursor/mcp.json": "Cursor",
        ".cursor/hooks.json": "Cursor",
        ".cursor/rules/data-platform.mdc": "Cursor",
        ".gemini/settings.json": "Gemini CLI",
        ".vscode/mcp.json": "Copilot (VS Code)",
        ".opencode/opencode.json": "OpenCode",
    }.get(target, "—")


# ------------------------------------------------------------------ targets --
def targets(root: str | Path) -> dict[str, str]:
    """Every generated file and its content, from the sources as they stand."""
    svs = servers(root)
    return {
        ".codex/config.toml": render_codex(svs),
        ".cursor/mcp.json": render_cursor_mcp(svs),
        ".cursor/hooks.json": render_cursor_hooks(),
        ".cursor/rules/data-platform.mdc": render_cursor_rule(),
        ".gemini/settings.json": render_gemini(svs),
        ".vscode/mcp.json": render_vscode(svs),
        ".opencode/opencode.json": render_opencode(svs),
        "docs/HARNESSES.md": render_scorecard(),
    }


def check(root: str | Path) -> list[str]:
    """One line per config that is missing or differs from what the sources say."""
    root = Path(root)
    problems: list[str] = []
    for rel, content in targets(root).items():
        p = root / rel
        if not p.is_file():
            problems.append(f"{rel} is missing — that harness has no graph or no gate; run `pf context refresh`")
        elif p.read_text(encoding="utf-8") != content:
            problems.append(f"{rel} is stale against .mcp.json — run `pf context refresh`")
    return problems


def write_all(root: str | Path) -> list[Path]:
    """Write every target that differs. Returns what changed."""
    root = Path(root)
    changed: list[Path] = []
    for rel, content in targets(root).items():
        p = root / rel
        if p.is_file() and p.read_text(encoding="utf-8") == content:
            continue
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        changed.append(p)
    return changed
