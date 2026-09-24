"""An accepted decision is corrected by adding a record, not by editing one.

`decisions/README.md` has said "Never delete one; supersede it" since the log
existed, and nothing enforced it. These cases pin both directions: an edit to
an accepted record is refused, and the three ways a record legitimately changes
are not.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from pf.loops.gate import check_record_immutability

POLICY = "version: 1\nrecords_immutable:\n  - '**/decisions/ADR-*.md'\n"

ACCEPTED = """# ADR-0001 — A decision

**Status:** accepted · **Date:** 2026-01-01

## Context

The original reasoning.
"""

DRAFT = ACCEPTED.replace("**Status:** accepted", "**Status:** proposed")


def _repo(tmp_path: Path, record: str = ACCEPTED) -> tuple[Path, str]:
    """A git repo holding one committed decision record."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    (tmp_path / "gate.yaml").write_text(POLICY, encoding="utf-8")
    rel = "groups/g/projects/p/decisions/ADR-0001-a-decision.md"
    target = tmp_path / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(record, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "seed"], cwd=tmp_path, check=True)
    return target, rel


def test_editing_an_accepted_record_is_refused(tmp_path: Path) -> None:
    target, rel = _repo(tmp_path)
    target.write_text(ACCEPTED.replace("The original reasoning.", "Rewritten."), encoding="utf-8")
    results = check_record_immutability([rel], tmp_path)
    assert [r.verdict for r in results] == ["deny"]
    assert results[0].rule == "records_immutable"


def test_marking_a_record_superseded_is_how_a_correction_lands(tmp_path: Path) -> None:
    """The Status line is the one part that may change in place."""
    target, rel = _repo(tmp_path)
    target.write_text(
        ACCEPTED.replace("**Status:** accepted", "**Status:** superseded by ADR-0002"),
        encoding="utf-8",
    )
    assert check_record_immutability([rel], tmp_path) == []


def test_a_record_still_being_drafted_is_not_frozen(tmp_path: Path) -> None:
    target, rel = _repo(tmp_path, DRAFT)
    target.write_text(DRAFT.replace("The original reasoning.", "Still drafting."), encoding="utf-8")
    assert check_record_immutability([rel], tmp_path) == []


def test_a_brand_new_record_is_an_addition_not_an_edit(tmp_path: Path) -> None:
    _, _ = _repo(tmp_path)
    rel = "groups/g/projects/p/decisions/ADR-0002-another.md"
    (tmp_path / rel).write_text(ACCEPTED, encoding="utf-8")
    assert check_record_immutability([rel], tmp_path, added=[rel]) == []


def test_an_uncommitted_record_is_an_addition_even_if_the_caller_forgot(tmp_path: Path) -> None:
    """`added=None` means unknown; git is the authority, not the caller."""
    _, _ = _repo(tmp_path)
    rel = "groups/g/projects/p/decisions/ADR-0003-new.md"
    (tmp_path / rel).write_text(ACCEPTED, encoding="utf-8")
    assert check_record_immutability([rel], tmp_path) == []


def test_an_untouched_record_is_not_flagged(tmp_path: Path) -> None:
    _, rel = _repo(tmp_path)
    assert check_record_immutability([rel], tmp_path) == []


def test_files_outside_the_pattern_are_not_judged(tmp_path: Path) -> None:
    _repo(tmp_path)
    other = tmp_path / "groups/g/projects/p/transform/models/m.sql"
    other.parent.mkdir(parents=True, exist_ok=True)
    other.write_text("select 1", encoding="utf-8")
    rel = "groups/g/projects/p/transform/models/m.sql"
    assert check_record_immutability([rel], tmp_path) == []


def test_no_policy_means_no_opinion(tmp_path: Path) -> None:
    """A repo that has not adopted the rule is not silently governed by it."""
    target, rel = _repo(tmp_path)
    (tmp_path / "gate.yaml").write_text("version: 1\n", encoding="utf-8")
    target.write_text(ACCEPTED.replace("The original reasoning.", "Rewritten."), encoding="utf-8")
    assert check_record_immutability([rel], tmp_path) == []


@pytest.mark.parametrize("status", ["accepted", "Accepted", "accepted · **Stage:** `dialect`"])
def test_accepted_is_recognised_however_the_line_is_written(tmp_path: Path, status: str) -> None:
    record = ACCEPTED.replace("**Status:** accepted", f"**Status:** {status}")
    target, rel = _repo(tmp_path, record)
    target.write_text(record.replace("The original reasoning.", "Rewritten."), encoding="utf-8")
    assert [r.verdict for r in check_record_immutability([rel], tmp_path)] == ["deny"]
