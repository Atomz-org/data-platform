"""The ontology-design skill, checked against the platform it describes.

A skill is a document, so nothing fails when it goes stale: it keeps telling an
agent to run a command that was renamed, or to edit a file that moved, and the
agent does what it is told. The skills that drive an agent *step* are covered by
eval cases; this one guides the interactive agent, so its evidence is this —
every command it names resolves in the CLI, every path it names exists, and the
three tiers it promises are the three tiers that are built.
"""

from __future__ import annotations

import re

import pytest
from conftest import REPO_ROOT

SKILL = REPO_ROOT / "platform" / "toolkits" / "ontology-design" / "skills" / "design-ontology" / "SKILL.md"


def _text() -> str:
    return SKILL.read_text(encoding="utf-8")


def _cli() -> set[str]:
    """Every command and command group the CLI registers, as `pf x` / `pf x y`."""
    from pf.cli import app

    names: set[str] = set()
    for c in app.registered_commands:
        names.add(c.name or c.callback.__name__.replace("_", "-"))
    for t in app.registered_groups:
        group = t.name or t.typer_instance.info.name or ""
        names.add(group)
        for c in t.typer_instance.registered_commands:
            names.add(f"{group} {c.name or c.callback.__name__.replace('_', '-')}")
        for sub in t.typer_instance.registered_groups:
            sub_name = sub.name or sub.typer_instance.info.name or ""
            names.add(f"{group} {sub_name}")
            for c in sub.typer_instance.registered_commands:
                names.add(f"{group} {sub_name} {c.name or c.callback.__name__.replace('_', '-')}")
    return names


def test_the_skill_is_addressable() -> None:
    assert SKILL.is_file()
    assert _text().startswith("---\nname: design-ontology\n")


@pytest.mark.parametrize("command", sorted({
    # Every `pf …` invocation the skill tells an agent to run, less the
    # placeholders it shows in angle brackets.
    " ".join(w for w in line.split() if not w.startswith(("<", "--", "`")))
    for line in re.findall(r"`?(pf [a-z][\w -]*)", (SKILL.read_text(encoding="utf-8")))
}))
def test_every_command_the_skill_names_exists(command: str) -> None:
    words = command.split()[1:]
    known = _cli()
    for depth in (3, 2, 1):
        if len(words) >= depth and " ".join(words[:depth]) in known:
            return
    pytest.fail(f"`{command}` is in the skill and not in the CLI")


def test_every_path_the_skill_names_exists() -> None:
    """Including the per-group and per-project shapes, resolved against a real
    group — a skill that names a file nobody has is a skill nobody can follow."""
    text = _text()
    literal = [
        "platform/src/pf/ontology/concepts.yaml",
        "platform/okf/",
    ]
    for rel in literal:
        assert rel in text, f"the skill no longer names {rel}"
        assert (REPO_ROOT / rel.rstrip("/")).exists(), f"{rel} is named in the skill and does not exist"

    group = next(g for g in sorted((REPO_ROOT / "groups").iterdir()) if (g / "ontology" / "extension.yaml").is_file())
    assert "groups/<group>/ontology/extension.yaml" in text
    assert (group / "ontology" / "extension.yaml").is_file()
    assert "groups/<g>/okf/" in text
    assert (group / "okf" / "index.md").is_file(), "the skill promises a family bundle that is not built"


def test_the_three_tiers_the_skill_promises_are_the_three_that_are_built() -> None:
    from pf.projections import okf

    group = next(g.name for g in sorted((REPO_ROOT / "groups").iterdir()) if (g / "ontology").is_dir())
    platform_files = okf.build_platform(REPO_ROOT)
    group_files = okf.build_group(REPO_ROOT, group)

    assert "okf_x_scope: platform" in platform_files["index.md"]
    assert "okf_x_scope: group" in group_files["index.md"]
    # and the chain the skill describes: family → platform
    assert "okf_x_platform_bundle:" in group_files["index.md"]
