"""The otop manifest's timestamps.

`created_at` and `implemented_at` come from git rather than from `now()`,
specifically so that regenerating the manifest is not a diff. That only holds if
the value is a property of the commit — the same commit has to export to the
same string everywhere, or the manifest churns between whoever ran it last.

It did churn, 42 entries at a time, because the export asked git for the commit
in *local* time and then appended a literal `Z`. A host at UTC+2 and a container
at UTC wrote two different instants for one commit, each claiming to be UTC.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
from pf.projections.otop import _as_ts, _authored


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A one-commit repository, committed at a known non-UTC offset."""
    def git(*args: str, **env: str) -> None:
        subprocess.run(["git", *args], cwd=tmp_path, check=True,
                       capture_output=True,
                       env={**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null",
                            "GIT_CONFIG_SYSTEM": "/dev/null", **env})

    git("init", "-q")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "t")
    (tmp_path / "policy.yaml").write_text("policies: []\n")
    git("add", "policy.yaml")
    # 22:01:06 at +02:00 is 20:01:06Z. The two are what the bug confused.
    stamp = "2026-08-13T22:01:06+02:00"
    git("commit", "-q", "-m", "p",
        GIT_AUTHOR_DATE=stamp, GIT_COMMITTER_DATE=stamp)
    return tmp_path


@pytest.mark.parametrize("tz", ["UTC", "Europe/Berlin", "Asia/Kolkata",
                                "America/Los_Angeles"])
def test_the_same_commit_exports_the_same_instant_everywhere(
        repo: Path, tz: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """The property the manifest depends on, and the one that was broken."""
    monkeypatch.setenv("TZ", tz)
    assert _authored(repo, "policy.yaml") == "2026-08-13T20:01:06Z"


def test_the_exported_stamp_is_the_real_instant_not_a_local_clock(
        repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A `Z` on a local reading is wrong even when nothing else disagrees."""
    monkeypatch.setenv("TZ", "Europe/Berlin")  # +02:00 on this date
    assert _authored(repo, "policy.yaml") != "2026-08-13T22:01:06Z"


def test_a_path_git_does_not_know_falls_back_rather_than_emptying(
        repo: Path) -> None:
    """An untracked artefact still gets a timestamp; otop requires one."""
    assert _authored(repo, "nope.yaml").endswith("Z")


@pytest.mark.parametrize("value,expected", [
    ("2026-08-13T22:01:06+02:00", "2026-08-13T20:01:06Z"),
    ("2026-08-13T20:01:06+00:00", "2026-08-13T20:01:06Z"),
    ("2026-08-13T01:31:06+05:30", "2026-08-12T20:01:06Z"),
    ("not a timestamp", ""),
    ("", ""),
])
def test_offsets_normalise_to_utc(value: str, expected: str) -> None:
    assert _as_ts(value) == expected
