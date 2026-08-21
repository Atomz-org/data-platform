"""Every diagram in the repo, and the map that has to stay true.

A mermaid diagram fails in one direction only and fails quietly: GitHub renders
an unparseable source as a red box while every job around it exits 0. Worse are
the sources that *do* parse and lie — an edge to a node nobody declared draws to
an empty box, and two boxes sharing an id are merged, so one layer of the
diagram silently disappears.

`docs/ARCHITECTURE.md` carries the same risk one level up. A hand-drawn map goes
stale the first time a directory moves, and a stale map is worse than none: it
sends a reader confidently to a path that no longer exists, which is exactly the
cost it was written to remove. So it is generated, and checked here.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import REPO_ROOT
from pf.archmap import drift, gather, render
from pf.mermaid import blocks, lint

DOCS = REPO_ROOT / "docs"


def _markdown_with_diagrams() -> list[Path]:
    return sorted(p for p in DOCS.rglob("*.md") if blocks(p.read_text()))


# ------------------------------------------------------------- diagrams -----
def test_the_repo_actually_has_diagrams_to_check() -> None:
    """Guards the guard: if the glob broke, everything below passes vacuously."""
    found = _markdown_with_diagrams()
    assert found, "no markdown in docs/ contains a mermaid block"


@pytest.mark.parametrize("doc", _markdown_with_diagrams(), ids=lambda p: p.name)
def test_every_diagram_parses_and_says_what_it_looks_like(doc: Path) -> None:
    problems: list[str] = []
    for i, block in enumerate(blocks(doc.read_text()), 1):
        problems += [f"{doc.name} diagram {i}: {p}" for p in lint(block)]
    assert not problems, "\n".join(problems)


def test_the_linter_can_fail() -> None:
    """A checker that cannot fail is a checker nobody should trust.

    Each case below is a real mermaid failure mode that still renders.
    """
    assert lint('flowchart LR\n  A["a"] --> B\n'), "missed an undeclared node"
    assert lint('flowchart LR\n  A["a"]\n  A["b"]\n'), "missed a duplicate id"
    assert lint('flowchart LR\n  A["a"]\n  class A ghost\n'), "missed an undefined class"
    assert lint('flowchart LR\n  A["Name <addr@host>"]\n'), "missed a raw angle bracket"
    assert not lint('flowchart LR\n  A["a"] --> B["b"]\n'), "false positive on a valid diagram"


def test_dotted_and_labelled_edges_are_understood() -> None:
    """`-.label.->` hides its label *inside* the operator, not in brackets.

    A naive scan reads fragments of the label as node ids and reports failures
    that do not exist — which is how a linter gets switched off.
    """
    good = ('flowchart LR\n  A["a"]\n  B["b"]\n'
            '  A -.provenance.-> B\n  A -->|plain| B\n  A -.-> B\n')
    assert not lint(good)


# ------------------------------------------------------------ the map -------
def test_the_committed_map_matches_the_repository() -> None:
    """Run `uv run pf arch build` if this fails — the repository is the source."""
    assert drift(REPO_ROOT) == ""


def test_the_map_is_rendered_deterministically() -> None:
    """It is compared byte for byte, so two renders must agree.

    Set iteration order is the usual way this breaks, and it breaks
    intermittently — the worst failure mode for something that gates a build.
    """
    assert render(gather(REPO_ROOT)) == render(gather(REPO_ROOT))


def test_the_map_counts_real_things() -> None:
    """The numbers must come from the repository, not from a constant."""
    f = gather(REPO_ROOT)
    assert f.projects == len(list((REPO_ROOT / "groups").glob("*/projects/*")))
    assert f.toolkits and all((REPO_ROOT / "platform" / "toolkits" / t).is_dir()
                              for t in f.toolkits)
    assert f.capabilities, "no capabilities discovered"


def test_the_map_survives_a_repo_with_nothing_in_it(tmp_path: Path) -> None:
    """`gather` runs against a checkout mid-scaffold, so it must not assume.

    A generator that raises on an empty tree fails exactly when someone is
    setting the repository up and has the least context to debug it.
    """
    (tmp_path / "platform").mkdir()
    (tmp_path / "groups").mkdir()
    f = gather(tmp_path)
    assert f.projects == 0
    assert render(f)


def test_the_map_is_worth_reading_rather_than_grepping() -> None:
    """It replaces exploration, so it has to stay cheaper than exploring.

    No hard ceiling — this is one document read on demand, not always-on
    context — but a map that grows without bound has become the thing it
    replaced.
    """
    text = (DOCS / "ARCHITECTURE.md").read_text()
    approx_tokens = len(text) // 4
    assert 500 < approx_tokens < 6000, (
        f"the architecture map is ~{approx_tokens} tokens; summarise a section "
        f"into a table rather than enumerating it"
    )
