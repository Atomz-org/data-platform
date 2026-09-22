"""The harness configs: one source, every tool, and a scorecard that does not flatter.

`AGENTS.md` made the rules agnostic. These guard the layer a rule cannot
provide — the MCP servers a tool needs to ask the graph, in that tool's own
format, and the hooks a tool needs to be stopped — and the one property the
whole layer stands on:

  the scorecard is honest     a tool that reads "gated" and is not is worse
                                than one that knows it is not. No harness but
                                Claude Code claims a pre-tool hook; Cursor is
                                "partial" and says which half.

  one source                  every config lists the servers `.mcp.json` lists,
                                including the `pf` server the plugin file
                                carries, or the graph is missing from exactly
                                the tools that cannot load a Claude plugin.

  Claude's placeholder is      `${CLAUDE_PROJECT_DIR}` means nothing to Codex.
    rewritten, per harness      Left in, a server launches with a literal
                                dollar sign in its path and no error.

  the guard has no             `git commit -m "never use --no-verify"` is a
    false positives             commit that must go through. The upstream this
                                is ported from rewrote its matcher over exactly
                                that case; the table here is what keeps it.
"""

from __future__ import annotations

import importlib.util
import json
import tomllib
from pathlib import Path

import pytest
from conftest import REPO_ROOT
from pf import harness
from pf.harness import HARNESSES, TARGETS, check, servers, targets, write_all

ROOT = REPO_ROOT


def _tree(tmp_path: Path) -> Path:
    """A root with a Claude `.mcp.json` and a plugin `.mcp.json`, nothing else."""
    (tmp_path / "platform" / "toolkits" / "power-tools").mkdir(parents=True)
    (tmp_path / "groups").mkdir()
    (tmp_path / ".mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "graphify": {
                        "command": "uvx",
                        "args": ["graphify-mcp", "${CLAUDE_PROJECT_DIR}/graphify-out/graph.json"],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "platform" / "toolkits" / "power-tools" / ".mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "pf": {
                        "command": "uv",
                        "args": ["run", "pf", "mcp"],
                        "env": {"PF_PROJECT_DIR": "${CLAUDE_PROJECT_DIR}"},
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    return tmp_path


# --------------------------------------------------------------- one source --
def test_the_plugin_server_reaches_every_harness(tmp_path: Path) -> None:
    """`pf` lives in the plugin's `.mcp.json`. A harness that cannot load Claude
    plugins must still get it, or the graph is absent from the tools that
    most need to be told about it."""
    root = _tree(tmp_path)
    names = {s.name for s in servers(root)}
    assert names == {"graphify", "pf"}

    rendered = targets(root)
    for rel in (
        ".codex/config.toml",
        ".cursor/mcp.json",
        ".gemini/settings.json",
        ".vscode/mcp.json",
        ".opencode/opencode.json",
    ):
        assert "pf" in rendered[rel] and "graphify" in rendered[rel], f"{rel} is missing a server"


def test_claudes_placeholder_is_rewritten_for_each_harness(tmp_path: Path) -> None:
    """Left in, `${CLAUDE_PROJECT_DIR}` is a literal path component to every
    other tool, and a server that fails to find its graph file starts fine."""
    root = _tree(tmp_path)
    r = targets(root)

    for rel in (".cursor/mcp.json", ".vscode/mcp.json"):
        assert "${workspaceFolder}/graphify-out/graph.json" in r[rel], rel
        assert "${CLAUDE_PROJECT_DIR}" not in r[rel], rel

    for rel in (".codex/config.toml", ".gemini/settings.json", ".opencode/opencode.json"):
        assert '"graphify-out/graph.json"' in r[rel], rel
        assert "${CLAUDE_PROJECT_DIR}" not in r[rel], rel

    # A bare placeholder as an env value means "here", not "".
    codex = tomllib.loads(r[".codex/config.toml"])
    assert codex["mcp_servers"]["pf"]["env"]["PF_PROJECT_DIR"] == "."


def test_every_structured_target_parses_in_its_own_format(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    r = targets(root)
    codex = tomllib.loads(r[".codex/config.toml"])
    assert set(codex["mcp_servers"]) == {"graphify", "pf"}
    assert codex["sandbox_mode"] == "workspace-write"
    assert "AGENTS.md" in codex["persistent_instructions"]

    assert set(json.loads(r[".cursor/mcp.json"])["mcpServers"]) == {"graphify", "pf"}
    assert set(json.loads(r[".gemini/settings.json"])["mcpServers"]) == {"graphify", "pf"}
    vscode = json.loads(r[".vscode/mcp.json"])["servers"]
    assert all(v["type"] == "stdio" for v in vscode.values())
    oc = json.loads(r[".opencode/opencode.json"])
    assert oc["instructions"] == ["AGENTS.md"]
    assert oc["mcp"]["pf"]["command"] == ["uv", "run", "pf", "mcp"]

    hooks = json.loads(r[".cursor/hooks.json"])["hooks"]
    assert set(hooks) == {"beforeShellExecution", "afterFileEdit"}
    assert all(harness.CURSOR_HOOK in h["command"] for ev in hooks.values() for h in ev)


def test_rendering_is_deterministic_and_check_names_each_drift(tmp_path: Path) -> None:
    """Compared byte for byte in CI, so two renders must agree; and the check
    must name the file and the one command."""
    root = _tree(tmp_path)
    assert targets(root) == targets(root)

    problems = check(root)
    assert len(problems) == len(TARGETS)
    assert all("is missing" in p and "pf context refresh" in p for p in problems)

    written = {p.relative_to(root).as_posix() for p in write_all(root)}
    assert written == set(TARGETS)
    assert check(root) == []
    assert write_all(root) == [], "a second write must change nothing"

    (root / ".codex" / "config.toml").write_text("# edited by hand\n", encoding="utf-8")
    [problem] = check(root)
    assert problem.startswith(".codex/config.toml is stale")


def test_a_server_added_to_the_source_reaches_every_config(tmp_path: Path) -> None:
    """The reason the layer is generated: add a server once, not six times."""
    root = _tree(tmp_path)
    write_all(root)
    src = json.loads((root / ".mcp.json").read_text(encoding="utf-8"))
    src["mcpServers"]["wren"] = {"command": "uvx", "args": ["wren-mcp"]}
    (root / ".mcp.json").write_text(json.dumps(src), encoding="utf-8")

    stale = check(root)
    assert len(stale) == 5, "every server-bearing config went stale, and only those"
    write_all(root)
    for rel in (
        ".codex/config.toml",
        ".cursor/mcp.json",
        ".gemini/settings.json",
        ".vscode/mcp.json",
        ".opencode/opencode.json",
    ):
        assert "wren" in (root / rel).read_text(encoding="utf-8"), rel


# ----------------------------------------------------------------- honesty --
def test_no_harness_but_claude_claims_a_pre_tool_hook() -> None:
    """The scorecard's one invariant. A tool that reads 'gated' and is not has
    been lied to by the file meant to prevent exactly that."""
    for h in HARNESSES:
        if h.name == "Claude Code":
            assert h.pre_tool_gate.startswith("hook")
            assert h.provenance.startswith("hooks")
        elif h.name == "Cursor":
            assert h.pre_tool_gate.startswith("partial"), "Cursor has half a hook and must say so"
            assert h.provenance == "none"
        else:
            assert h.pre_tool_gate.startswith("none"), f"{h.name} has no tool hooks"
            assert h.provenance == "none", f"{h.name} writes no provenance"
        assert "pre-commit" in h.commit_gate, f"{h.name}: the commit gate is the shared backstop"


def test_the_scorecard_says_rule_where_nothing_enforces() -> None:
    card = harness.render_scorecard()
    assert "| Codex CLI |" in card and "none — commit gate only" in card
    assert "partial" in card and "after the fact" in card
    assert "*rule*" in card, "the word that carries the meaning must be defined on the page"


def test_this_repo_is_current() -> None:
    """Run `uv run pf context refresh` if this fails."""
    assert check(ROOT) == [], "harness configs are stale — run `uv run pf context refresh`"


# ------------------------------------------------------------ cursor hook --
def _hook():
    spec = importlib.util.spec_from_file_location("cursor_hook", ROOT / "platform" / "hooks" / "cursor_hook.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize(
    "command,bypasses",
    [
        ('git commit -m "note: never use --no-verify here"', False),
        ("git commit -F msg.txt", False),
        ('git commit --message="--no-verify is bad"', False),
        ("git push -n origin main", False),  # -n is dry-run for push
        ("git status --no-verify", False),  # not a commit or push
        ("echo hello", False),
        ("git commit --no-verify -m x", True),
        ("git commit -am x -n", True),
        ("git commit -an -m x", True),
        ("git commit -n", True),
        ("git push --no-verify", True),
        ("uv run pytest && git push --no-verify origin main", True),
    ],
)
def test_the_no_verify_guard_is_flag_position_aware(command: str, bypasses: bool) -> None:
    assert _hook().bypasses_hooks(command) is bypasses


def test_the_guard_never_fails_closed_on_bad_input() -> None:
    """A hook that blocks every command over a parse error blocks the editor."""
    mod = _hook()
    assert mod.bypasses_hooks('git commit -m "unterminated') is False
    assert mod.bypasses_hooks("") is False
