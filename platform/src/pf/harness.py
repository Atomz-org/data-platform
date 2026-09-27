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

    the gate       `gate.yaml` fired through Claude Code's PreToolUse hook and
                   nowhere else. A rule an agent must remember is not
                   enforcement. `pf.agenthook` is now the gate, the permission
                   lists, provenance, the formatter and the turn-one context,
                   written once; `platform/hooks/agent_hook.py <harness> <event>`
                   reaches it from any harness whose hooks are wired to it.

This module treats the per-harness config layer the way the platform treats
every derived artefact: **generated from one source, committed for review,
and checked for drift by `pf context check`.** The sources are what they were —
`.mcp.json` for the servers, `.claude/settings.json` for the permission lists,
`gate.yaml` for what is blocked, `AGENTS.md` for the rules — and the targets are
rendered from them, never hand-edited.

## One module per harness

What each harness needs is declared in `pf.harnesses.<name>`: its configs, its
scorecard row, and — once its hooks call the core — its dialect. This module
holds only what they share: the server list and its placeholder rewriting, the
hook command, the scorecard, and `targets` / `check` / `write_all` over the
registry. Adding a harness never edits this file.

## What each harness gets, honestly

Enforcement exists where a hook calls the core, and the scorecard in
`docs/HARNESSES.md` says, per cell, what is a hook and what is only a rule.
Where a harness only half honours its config, its module says that too, and
the scorecard prints it. A scorecard that claimed more than the configs
deliver would be the worst outcome: a tool believing it is gated when it is
not.

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

SCORECARD = "docs/HARNESSES.md"

#: The one hook entry point; every harness's config calls it with its own name.
AGENT_HOOK = "platform/hooks/agent_hook.py"

#: The repo root, from wherever the harness runs a hook. Several harnesses
#: export no project variable, and a session may be started inside a project;
#: git answers from any depth, and in a worktree it names the worktree.
ROOT_EXPR = '"$(git rev-parse --show-toplevel)"'


def hook_command(harness: str, event: str, root: str = ROOT_EXPR) -> str:
    return f"uv run --quiet --project {root} python {root}/{AGENT_HOOK} {harness} {event}"


def claude_style_hooks(harness: str, tools: str, *, post: bool = True) -> dict[str, Any]:
    """The `{"hooks": {Event: [{matcher, hooks: [...]}]}}` shape Claude Code
    introduced and Codex and Junie read as-is."""

    def one(event: str, matcher: str | None = None) -> list[dict[str, Any]]:
        e: dict[str, Any] = {"hooks": [{"type": "command", "command": hook_command(harness, event), "timeout": 60}]}
        return [{"matcher": matcher, **e}] if matcher else [e]

    hooks: dict[str, Any] = {"SessionStart": one("session"), "PreToolUse": one("pre", tools)}
    if post:
        hooks["PostToolUse"] = one("post", tools)
    hooks["Stop"] = one("stop")
    return {"hooks": hooks}


def ask_prefixes(root: str | Path) -> list[str]:
    """`Bash(<prefix>:*)` entries of the root settings' `ask` list — what a
    harness that prompts a person itself is given to prompt for."""
    p = Path(root) / ".claude" / "settings.json"
    try:
        perms = (json.loads(p.read_text(encoding="utf-8")) or {}).get("permissions") or {}
    except (OSError, json.JSONDecodeError):
        return []
    out = []
    for spec in perms.get("ask") or []:
        spec = str(spec)
        if spec.startswith("Bash(") and spec.endswith(")"):
            out.append(spec[5:-1].removesuffix(":*").strip())
    return out


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


def json_text(obj: Any) -> str:
    return json.dumps(obj, indent=2, sort_keys=False) + "\n"


def toml_str(s: str) -> str:
    return json.dumps(s)  # a JSON string literal is a valid TOML basic string


def claude_shape(svs: list[Server], token: str | None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for s in svs:
        s = s.with_project(token)
        spec: dict[str, Any] = {"command": s.command, "args": list(s.args)}
        if s.env:
            spec["env"] = dict(s.env)
        out[s.name] = spec
    return out


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
    skills: str = "none"
    agents: str = "none"
    #: The generated file whose presence makes `pre_tool_gate` true, and the
    #: harness name it must pass `agent_hook.py` on its pre-tool event. The
    #: tests hold every row that says *hook* to this.
    hook_config: str = ""
    hook_name: str = ""


#: The column every harness that reads `.agents/skills/` shares.
SKILLS_CELL = "`.agents/skills/` — toolkits, commands; a group's under the group"

CLAUDE_ROW = Harness(
    "Claude Code",
    "`CLAUDE.md` + hooks",
    "`.mcp.json` + power-tools plugin",
    "hook — `pre_tool_use.py` on every Edit/Write",
    "pre-commit",
    "hooks write stages 01–03",
    "injected on turn one",
    "`session_start.sh`",
    "plugins — every toolkit",
    "power-tools plugin",
)

PROMPT_ONLY_ROW = Harness(
    "Prompt-only (Continue, Ollama, mlx)",
    "paste `AGENTS.md`",
    "none",
    "none",
    "pre-commit",
    "none",
    "rule",
    "rule",
)


def harnesses() -> tuple[Harness, ...]:
    """What is *true* for each tool, not what would be nice. "rule" means the
    protocol asks for it and nothing enforces it; that word is the point."""
    from pf.harnesses import specs

    return (CLAUDE_ROW, *(r for s in specs() for r in s.rows), PROMPT_ONLY_ROW)


def __getattr__(name: str) -> Any:
    """`HARNESSES` and `TARGETS`, computed: a harness is added by adding a
    module to `pf.harnesses`, never by editing a list here."""
    if name == "HARNESSES":
        return harnesses()
    if name == "TARGETS":
        # The fixed files — what a render from no sources at all still writes.
        return tuple(targets(Path("/nonexistent-pf-root")))
    raise AttributeError(name)


def render_scorecard() -> str:
    """`docs/HARNESSES.md`: per harness, what is enforced and what is asked."""
    from pf.harnesses import Ctx, specs

    lines = [
        "# Harnesses — what each agent tool actually gets",
        "",
        "GENERATED by `pf context refresh` from `platform/src/pf/harness.py` and",
        "`platform/src/pf/harnesses/`. Do not hand-edit; `pf context check` fails when",
        "this file and the code disagree.",
        "",
        "The rules are written once, per execution scope, in `AGENTS.md`, and every",
        "tool reaches them. The **enforcement** is written once too: `pf.agenthook` is the",
        "gate, the permission lists, provenance, the formatter and the turn-one context,",
        "and `platform/hooks/agent_hook.py <harness> <event>` reaches it from each tool's",
        "own hook system, where that tool's config wires it. A hook can stop an action;",
        "a rule can only ask. This table says which is which. Where it says *rule*,",
        "nothing checks — and the commit gate (`platform/hooks/pre_commit.sh`,",
        "`pf install-hook`) is the backstop every tool shares.",
        "",
        "Every *hook* cell outside Claude Code is the same check: `gate.yaml`, then the",
        "`deny`/`ask` lists of `.claude/settings.json` (and the project's, in a project",
        "session) — which Claude Code applies itself and no other tool reads — then",
        "provenance.",
        "",
        (
            "| Harness | Entry point | Graph (MCP) | Pre-tool gate | Commit gate | Provenance | Memory "
            "| Session context | Skills | Subagents |"
        ),
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for h in harnesses():
        lines.append(
            f"| {h.name} | {h.entry} | {h.graph} | {h.pre_tool_gate} | {h.commit_gate} "
            f"| {h.provenance} | {h.memory} | {h.session_context} | {h.skills} | {h.agents} |"
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
    empty = Ctx(Path("/nonexistent-pf-root"), [], [])
    for s in specs():
        for rel in s.render(empty):
            lines.append(f"| {s.owner} | `{rel}` | `pf context refresh` |")
    lines += [
        "",
        "Plus, from the toolkits (`pf.harness_assets`): every skill linked into",
        "`.agents/skills/` — the one directory every harness above discovers — the",
        "power-tools commands as skills beside them, and the power-tools subagents in",
        "the format of each harness that declares one.",
        "",
    ]
    launch = [s.launch for s in specs() if s.launch]
    lines += [
        "## Start a session",
        "",
        "```bash",
        f"bin/agent-here {'|'.join(['claude', *launch])} [args]",
        "```",
        "",
        "Each harness finds its generated config from the checkout on its own; the",
        "launcher adds only what must be decided before the process starts — scratch",
        "files in `.tmp/`, `PF_AGENT` for memory notes, a warning when the commit gate",
        "is missing.",
        "",
        "## Verify",
        "",
        "```bash",
        "uv run pf context check              # every config above is current",
        "ls .git/hooks/pre-commit             # the commit gate is installed (pf install-hook)",
        "uv run pytest platform/tests/gate/test_agent_hooks.py   # every harness, same verdicts",
        "```",
        "",
    ]
    caveats = [line for s in specs() for line in s.caveats]
    if caveats:
        lines += ["## Where a harness only half honours its config", "", *caveats, ""]
    lines += [
        "Claiming more than this would leave a tool believing it is gated when it is",
        "not, which is the one outcome worse than an ungated tool that knows it.",
        "",
    ]
    return "\n".join(lines)


# ------------------------------------------------------------------ targets --
def targets(root: str | Path) -> dict[str, str]:
    """Every generated file and its content, from the sources as they stand."""
    from pf import harness_assets
    from pf.harnesses import Ctx, specs

    root = Path(root)
    ctx = Ctx(root, servers(root), ask_prefixes(root))
    out: dict[str, str] = {}
    for s in specs():
        out.update(s.render(ctx))
    out[SCORECARD] = render_scorecard()
    out.update(harness_assets.targets(root))
    return out


def check(root: str | Path) -> list[str]:
    """One line per config that is missing or differs from what the sources say."""
    from pf import harness_assets

    root = Path(root)
    problems: list[str] = []
    for rel, content in targets(root).items():
        p = root / rel
        if not p.is_file():
            problems.append(f"{rel} is missing — that harness has no graph or no gate; run `pf context refresh`")
        elif p.read_text(encoding="utf-8") != content:
            problems.append(f"{rel} is stale against its source — run `pf context refresh`")
    problems.extend(harness_assets.check_links(root))
    return problems


def write_all(root: str | Path) -> list[Path]:
    """Write every target that differs, and every skill link. Returns what changed."""
    from pf import harness_assets

    root = Path(root)
    changed: list[Path] = []
    for rel, content in targets(root).items():
        p = root / rel
        if p.is_file() and p.read_text(encoding="utf-8") == content:
            continue
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        changed.append(p)
    changed.extend(harness_assets.write_links(root))
    return changed
