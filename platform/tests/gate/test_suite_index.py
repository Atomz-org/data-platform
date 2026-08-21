"""The suite's own index, and the structure that makes it navigable.

An index generated before a test file was added answers "where is that tested"
with confident silence — worse than no index, because it is trusted. So the
index is checked by the suite it describes: add a test file without running
`pf test index` and this fails, naming the command.

The structural rules below are the other half. They are cheap to state and
expensive to rediscover: an ungrouped file is invisible in the index's own
grouping, and a file whose docstring says nothing contributes a blank row.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import REPO_ROOT
from pf.testmap import GROUPS, drift, render_index, scan, where

TESTS = REPO_ROOT / "platform" / "tests"


def test_the_committed_index_matches_the_suite() -> None:
    """Run `uv run pf test index` if this fails — the suite is the source."""
    assert drift(TESTS) == ""


def test_every_test_file_lives_in_a_named_group() -> None:
    """A file directly in tests/ has no group, so its directory names nothing.

    The directory *is* the first line of the index. A file that sits outside one
    is findable only by reading it, which is the cost this structure removes.
    """
    loose = [f.path.name for f in scan(TESTS) if not f.group]
    assert not loose, (
        f"{loose} sit directly in platform/tests/; move each into one of "
        f"{sorted(GROUPS)} or add a group for it"
    )


def test_every_group_is_glossed() -> None:
    """A directory with no gloss in GROUPS indexes as a bare name."""
    used = {f.group for f in scan(TESTS) if f.group}
    assert used <= set(GROUPS), (
        f"{sorted(used - set(GROUPS))} has no gloss in pf.testmap.GROUPS — "
        f"say what it guards, or fold it into a group that exists"
    )


def test_every_file_says_what_it_guards() -> None:
    """The first docstring line is the index entry. Blank means a blank row."""
    silent = [f.path.name for f in scan(TESTS) if not f.subject]
    assert not silent, f"{silent} have no module docstring to index"


def test_the_index_is_deterministic() -> None:
    """It is compared byte for byte, so rendering twice must agree.

    Set ordering is the usual way this breaks, and it breaks intermittently —
    the worst failure mode for a check that gates a build.
    """
    files = scan(TESTS)
    assert render_index(files) == render_index(scan(TESTS))
    assert render_index(files) == render_index(list(reversed(files)))


@pytest.mark.parametrize("term,expected", [
    ("policy", "test_policy_layering.py"),
    ("gate", "test_gate.py"),
    ("onboard", "test_onboard.py"),
])
def test_where_finds_the_obvious_file(term: str, expected: str) -> None:
    assert expected in {f.path.name for f in where(scan(TESTS), term)}


def test_where_searches_imports_not_only_prose() -> None:
    """Much of this suite imports inside the test body rather than at the top.

    An index built from top-level imports alone would report that nothing tests
    `pf.kg.build`, when three files do.
    """
    hits = {f.path.name for f in where(scan(TESTS), "pf.kg.build")}
    assert "test_kg_currency.py" in hits


def test_every_link_in_the_index_resolves() -> None:
    """A broken link renders as a link — it fails only when someone clicks it.

    The index lives *inside* the tests directory, so its links must be relative
    to that directory. A repo-relative path produces
    `platform/tests/platform/tests/...`, and a bare filename pointed at a
    sibling that stopped existing the moment files moved into groups.
    """
    import re

    text = (TESTS / "README.md").read_text()
    targets = re.findall(r"\]\(([^)]+\.py)\)", text)
    assert targets, "the index links to no files at all"
    broken = [t for t in targets if not (TESTS / t).exists()]
    assert not broken, f"index links point at nothing: {broken}"


def test_the_index_is_small_enough_to_be_worth_reading() -> None:
    """The point is to replace ~4,000 lines with something an agent will read.

    An index that grows with the suite stops being an index. The rollup this
    budget forces is the same one the context cards already make.
    """
    text = (TESTS / "README.md").read_text()
    approx_tokens = len(text) // 4
    assert approx_tokens < 1200, (
        f"the test index is ~{approx_tokens} tokens; summarise a group rather "
        f"than listing every file"
    )


def test_the_suite_is_reachable_from_the_repo_root() -> None:
    """`conftest.REPO_ROOT` is the one definition; prove it finds a real checkout."""
    assert (REPO_ROOT / "platform").is_dir()
    assert (REPO_ROOT / "groups").is_dir()
    assert Path(__file__).resolve().is_relative_to(REPO_ROOT)
