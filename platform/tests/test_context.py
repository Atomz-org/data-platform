"""Tests for the always-on context layer.

The properties worth pinning are the ones that fail silently. A rule that stops
being rendered is a rule switched off, and nothing anywhere reports it. A card
that drifts from its source is believed by every agent that reads it. And a card
that is not byte-stable defeats the prompt cache for every loop, every run, with
no error.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pf.capabilities import Capability
from pf.context import (
    TOOLKIT_INDEX, TOOLKIT_INDEX_BUDGET, TOOLS_CARD_BUDGET, build, is_stale,
    load_toolkits, problems, render_toolkit_index, render_tools_card,
)
from pf.kg.card import estimate_tokens


def _toolkit(root: Path, name: str, context: str = "", skill: str = "") -> Path:
    d = root / "platform" / "toolkits" / name
    (d / "skills").mkdir(parents=True, exist_ok=True)
    if context:
        (d / "CONTEXT.md").write_text(context)
    if skill:
        sd = d / "skills" / skill
        sd.mkdir(parents=True, exist_ok=True)
        (sd / "SKILL.md").write_text(
            f"---\nname: {skill}\ndescription: does {skill}.\n---\n# {skill}\n")
    return d


# ------------------------------------------------------------- discovery ----
def test_rules_and_when_are_read_from_frontmatter(tmp_path: Path) -> None:
    _toolkit(tmp_path, "kit",
             "---\nwhen: doing a thing.\nrules:\n  - never do the other thing.\n---\n",
             skill="do-thing")
    tk = load_toolkits(tmp_path)[0]
    assert tk.when == "doing a thing."
    assert tk.rules == ("never do the other thing.",)
    assert tk.skills[0].name == "do-thing"


def test_unparseable_frontmatter_is_reported_not_swallowed(tmp_path: Path) -> None:
    """The failure this layer is most exposed to. A list entry starting with a
    double quote parses as a quoted scalar followed by junk, the toolkit's rules
    vanish from every agent's context, and the index still renders fine."""
    _toolkit(tmp_path, "kit",
             '---\nwhen: x.\nrules:\n  - "Re-run" is only correct sometimes.\n---\n',
             skill="s")
    assert problems(tmp_path), "a rule silently contributing nothing must be reported"
    # Still renders, so one broken toolkit cannot take out the whole index.
    assert "kit" in render_toolkit_index(tmp_path)


def test_a_directory_with_no_skills_and_no_context_is_not_a_toolkit(tmp_path: Path) -> None:
    (tmp_path / "platform" / "toolkits" / "empty").mkdir(parents=True)
    assert load_toolkits(tmp_path) == []


# --------------------------------------------------------------- rendering --
def test_every_declared_rule_reaches_the_index(tmp_path: Path) -> None:
    """A rule that is declared but not rendered is a rule that was turned off by
    a refactor, and nothing else would catch it."""
    _toolkit(tmp_path, "kit",
             "---\nwhen: w.\nrules:\n  - alpha rule.\n  - beta rule.\n---\n", skill="s")
    out = render_toolkit_index(tmp_path)
    assert "alpha rule." in out
    assert "beta rule." in out


def test_the_index_omits_skill_descriptions(tmp_path: Path) -> None:
    """Descriptions live in each SKILL.md and load when the skill is invoked.
    Repeating them here costs always-on tokens to duplicate text the agent
    already gets at the moment it matters."""
    _toolkit(tmp_path, "kit", "---\nwhen: w.\n---\n", skill="do-thing")
    out = render_toolkit_index(tmp_path)
    assert "`do-thing`" in out
    assert "does do-thing." not in out


def test_a_project_with_no_capabilities_says_so(tmp_path: Path) -> None:
    (tmp_path / "groups" / "g" / "projects" / "p").mkdir(parents=True)
    assert "None enabled" in render_tools_card(tmp_path, "g", "p")


def test_capability_detection_follows_the_files_it_declares(tmp_path: Path,
                                                            monkeypatch) -> None:
    """Detection is derived from the capability's own `files`, so it cannot
    disagree with what was actually written into the project."""
    cap = Capability(name="demo", description="d", context="ctx",
                     rules=("do not edit the generated thing.",),
                     files={"reporting/README.md": "x"})
    monkeypatch.setattr("pf.context.CAPABILITIES", {"demo": cap})

    pdir = tmp_path / "groups" / "g" / "projects" / "p"
    pdir.mkdir(parents=True)
    assert "None enabled" in render_tools_card(tmp_path, "g", "p")

    (pdir / "reporting").mkdir()
    (pdir / "reporting" / "README.md").write_text("x")
    card = render_tools_card(tmp_path, "g", "p")
    assert "ctx" in card
    assert "do not edit the generated thing." in card


# ------------------------------------------------------------------ drift ---
def test_rendering_is_byte_stable(tmp_path: Path) -> None:
    """The whole caching design rests on this. A timestamp or a set iteration in
    either renderer would defeat every cache read on every loop, silently."""
    _toolkit(tmp_path, "b", "---\nwhen: w.\nrules:\n  - r.\n---\n", skill="s2")
    _toolkit(tmp_path, "a", "---\nwhen: w.\n---\n", skill="s1")
    (tmp_path / "groups" / "g" / "projects" / "p").mkdir(parents=True)

    assert render_toolkit_index(tmp_path) == render_toolkit_index(tmp_path)
    assert render_tools_card(tmp_path, "g", "p") == render_tools_card(tmp_path, "g", "p")


def test_build_is_idempotent_and_staleness_detects_an_edit(tmp_path: Path) -> None:
    _toolkit(tmp_path, "kit", "---\nwhen: w.\nrules:\n  - r.\n---\n", skill="s")
    (tmp_path / "groups" / "g" / "projects" / "p").mkdir(parents=True)

    build(tmp_path, "g", "p")
    assert not is_stale(tmp_path, "g", "p")

    # A hand-edit of a generated file is exactly what the gate denies and what
    # the next bootstrap would silently discard.
    (tmp_path / TOOLKIT_INDEX).write_text("hand-edited\n")
    assert is_stale(tmp_path, "g", "p")


# ----------------------------------------------------------------- budget ---
def test_the_shipped_index_is_within_budget() -> None:
    """The always-on tier is what silently inflates every session, so its budget
    is enforced rather than documented."""
    from pf import obs

    out = render_toolkit_index(obs.repo_root())
    assert estimate_tokens(out) <= TOOLKIT_INDEX_BUDGET


@pytest.mark.parametrize("group,project", [("acme", "acme-eu")])
def test_shipped_project_cards_are_within_budget(group: str, project: str) -> None:
    from pf import obs

    out = render_tools_card(obs.repo_root(), group, project)
    assert estimate_tokens(out) <= TOOLS_CARD_BUDGET


def test_the_shipped_toolkits_all_parse() -> None:
    from pf import obs

    assert problems(obs.repo_root()) == []
