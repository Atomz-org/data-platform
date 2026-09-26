"""The ask-through-wren skill, checked against the platform it drives.

An orchestration document: it names `pf` commands, MCP tools and sibling
skills, and an agent does what it names. So its evidence is that every command
resolves in the CLI, every MCP tool it names is served, and every skill it
routes to is shipped. What the road *does* is `test_tool_wren.py`'s to prove.
"""

from __future__ import annotations

import re

import pytest
from conftest import REPO_ROOT

TOOLKITS = REPO_ROOT / "platform" / "toolkits"
SKILL = TOOLKITS / "wren-analytics" / "skills" / "ask-through-wren" / "SKILL.md"


def _text() -> str:
    return SKILL.read_text(encoding="utf-8")


def _cli() -> set[str]:
    from pf.cli import app

    names: set[str] = set()

    def walk(typer_app, prefix: str) -> None:
        for c in typer_app.registered_commands:
            names.add(f"{prefix}{c.name or c.callback.__name__.replace('_', '-')}".strip())
        for g in typer_app.registered_groups:
            sub = g.name or g.typer_instance.info.name or ""
            names.add(f"{prefix}{sub}".strip())
            walk(g.typer_instance, f"{prefix}{sub} ")

    walk(app, "")
    # tool commands are registered lazily, by each tool's `commands` hook
    import typer
    from pf.tools import wren

    holder = typer.Typer()
    wren.register_commands(holder)
    walk(holder, "tool ")
    return names


def test_the_skill_is_addressable() -> None:
    assert _text().startswith("---\nname: ask-through-wren\n")


def _commands() -> set[str]:
    found: set[str] = set()
    for line in re.findall(r"`?(pf [a-z][\w -]*)", _text()):
        found.add(" ".join(w for w in line.split() if not w.startswith(("<", "--", "`", "\"", "["))))
    return found


@pytest.mark.parametrize("command", sorted(_commands()))
def test_every_command_the_skill_names_exists(command: str) -> None:
    words = command.split()[1:]
    known = _cli()
    for depth in (3, 2, 1):
        if len(words) >= depth and " ".join(words[:depth]) in known:
            return
    pytest.fail(f"`{command}` is in the skill and not in the CLI")


def test_every_mcp_tool_it_names_is_served() -> None:
    from pf.mcp import server

    named = set(re.findall(r"`(wren_[a-z_]+|query_metrics|list_metrics|execute_sql_query)`", _text()))
    assert named, "the skill names its tools"
    assert named <= set(server.TOOLS), sorted(named - set(server.TOOLS))


def test_every_skill_it_routes_to_exists() -> None:
    shipped = {p.parent.name for p in TOOLKITS.glob("*/skills/*/SKILL.md")} | {p.name for p in TOOLKITS.iterdir() if p.is_dir()}
    named = set(re.findall(r"`([a-z]+(?:-[a-z]+)+)(?::[^`]*)?`", _text()))
    named |= {m.split(":")[1].strip() for m in re.findall(r"`([a-z-]+: [a-z-]+)`", _text())}
    missing = {n for n in named - {"ask-through-wren", "wren-analytics"} if n not in shipped}
    assert not missing, f"routes to skills that do not exist: {sorted(missing)}"


def test_the_toolkit_is_routed_and_catalogued() -> None:
    assert "wren-analytics: ask-through-wren" in (TOOLKITS / "ROUTING.md").read_text(encoding="utf-8")
    assert "## wren-analytics" in (TOOLKITS / "TOOLKITS.md").read_text(encoding="utf-8")
