"""A session's working directories are inside the repo, not beside it.

The harness keeps a session's scratch files, background task output and pasted
images under a temporary root, and its runs under the Claude Code folder. Only
the runs were ever linked into the repo. Everything else landed somewhere the
operator could not find, was not covered by any backup, and disappeared with
the session — which makes it useless as a record of what an agent did.

The cases here pin the two properties that matter: the directories resolve
inside the repository, and the discovery that finds them survives the harness
renaming the segment they sit under. The second is the point. A link that
silently stops being made after a harness change is worse than no link, because
nothing reports it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pf import workflows as w

SESSION = "11111111-2222-3333-4444-555555555555"


@pytest.fixture
def harness(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    """A repo, and a Claude Code home, with the temp root pointed at tmp_path."""
    root = tmp_path / "repo"
    (root / ".git").mkdir(parents=True)
    home = tmp_path / "claude"
    (home / "projects" / w.slug(root) / SESSION).mkdir(parents=True)
    monkeypatch.setenv("TMPDIR", str(tmp_path / "tmp"))
    (tmp_path / "tmp").mkdir()
    return root, home


def _session(home: Path, root: Path) -> Path:
    return home / "projects" / w.slug(root) / SESSION


def test_a_session_directory_is_found_under_the_conventional_name(harness) -> None:
    root, _ = harness
    uid = __import__("os").getuid()
    made = Path(__import__("os").environ["TMPDIR"]) / f"claude-{uid}" / w.slug(root) / SESSION
    made.mkdir(parents=True)
    assert w.scratch_session(w.slug(root), SESSION) == made


def test_a_renamed_harness_segment_is_still_found(harness) -> None:
    """The robustness case: `claude-<uid>` is a convention, not an interface."""
    root, _ = harness
    moved = Path(__import__("os").environ["TMPDIR"]) / "claude-v2-something" / w.slug(root) / SESSION
    moved.mkdir(parents=True)
    assert w.scratch_session(w.slug(root), SESSION) == moved


def test_nothing_is_invented_when_there_is_nothing_to_find(harness) -> None:
    root, _ = harness
    assert w.scratch_session(w.slug(root), SESSION) is None


def test_a_missing_directory_is_created_when_asked(harness) -> None:
    """SessionStart runs before the harness makes the folder; a link made after
    the first write is already too late for it."""
    root, _ = harness
    made = w.scratch_session(w.slug(root), SESSION, create=True)
    assert made is not None and made.is_dir()
    assert made.name == SESSION


def test_a_stranger_directory_is_not_claimed(harness) -> None:
    """Both discovery legs require <slug>/<session> beneath, not just a name."""
    root, _ = harness
    (Path(__import__("os").environ["TMPDIR"]) / "claude-99" / "another-repo" / SESSION).mkdir(parents=True)
    assert w.scratch_session(w.slug(root), SESSION) is None


def test_every_pair_targets_a_path_inside_the_repository(harness) -> None:
    """The whole point: nothing this repo's sessions write lands outside it."""
    root, home = harness
    for kind, _path, target, _owner in w._pairs(_session(home, root), root):
        assert target.is_relative_to(root), f"{kind} points outside the repo: {target}"


def test_the_scratch_directories_are_all_covered(harness) -> None:
    root, home = harness
    kinds = {k for k, *_ in w._pairs(_session(home, root), root)}
    assert set(w.SCRATCH_KINDS) <= kinds
    assert {"runs", "scripts"} <= kinds, "the existing workflow links must survive"


def test_an_empty_session_links_cleanly(harness) -> None:
    """The ordinary SessionStart path: nothing written yet, so nothing to adopt."""
    root, home = harness
    sess = _session(home, root)
    reports = w.link(root, home, session_dir=sess)
    scratch = {r.kind: r for r in reports if r.kind in w.SCRATCH_KINDS}
    assert set(scratch) == set(w.SCRATCH_KINDS)
    for kind, r in scratch.items():
        assert r.ok, f"{kind}: {r.state} {r.note}"
        assert r.path.is_symlink(), f"{kind} was not replaced by a link"
        assert r.path.resolve().is_relative_to(root)


def test_linking_twice_changes_nothing(harness) -> None:
    root, home = harness
    sess = _session(home, root)
    w.link(root, home, session_dir=sess)
    again = [r for r in w.link(root, home, session_dir=sess) if r.kind in w.SCRATCH_KINDS]
    assert [r.state for r in again] == ["linked"] * len(w.SCRATCH_KINDS)


def test_a_file_written_through_the_link_lands_in_the_repo(harness) -> None:
    """End to end, because that is the claim being made to the operator."""
    root, home = harness
    sess = _session(home, root)
    w.link(root, home, session_dir=sess)
    tmp = w.scratch_session(w.slug(root), SESSION)
    assert tmp is not None
    (tmp / "scratchpad" / "note.md").write_text("written by the session", encoding="utf-8")
    landed = root / w.SCRATCH_DIR / SESSION / "scratchpad" / "note.md"
    assert landed.is_file()
    assert landed.read_text(encoding="utf-8") == "written by the session"


def test_a_relinked_session_repairs_a_link_pointing_elsewhere(harness) -> None:
    """If the harness moves, the next session must not keep the stale link."""
    root, home = harness
    sess = _session(home, root)
    w.link(root, home, session_dir=sess)
    tmp = w.scratch_session(w.slug(root), SESSION)
    assert tmp is not None
    elsewhere = root.parent / "elsewhere"
    elsewhere.mkdir()
    (tmp / "scratchpad").unlink()
    (tmp / "scratchpad").symlink_to(elsewhere)
    report = next(r for r in w.link(root, home, session_dir=sess)
                  if r.kind == "scratchpad")
    assert report.state == "refused"
    assert "already a link" in report.note


def test_creation_prefers_the_root_this_repo_already_uses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The bug this caught on a real machine: macOS sets TMPDIR to a per-user
    folder under /var/folders while the harness writes to /private/tmp. Creating
    the directory in the wrong root makes a link the harness never looks at, and
    nothing reports that -- the session just keeps writing outside the repo.

    Existence alone is too weak a signal, because this very function creates the
    empty directory that then makes the wrong root look plausible. Population is
    not: the root with the sessions in it is the one in use.
    """
    import os

    root = tmp_path / "repo"
    (root / ".git").mkdir(parents=True)
    decoy, real = tmp_path / "decoy", tmp_path / "real"
    seg = f"claude-{os.getuid()}"
    # The decoy exists and is even set up for this repo, but nothing lives there.
    (decoy / seg / w.slug(root)).mkdir(parents=True)
    for prior in ("aaaa", "bbbb", "cccc"):
        (real / seg / w.slug(root) / prior).mkdir(parents=True)
    monkeypatch.setenv("TMPDIR", str(decoy))
    monkeypatch.setattr(w, "_tmp_roots", lambda: [decoy, real])

    made = w.scratch_session(w.slug(root), SESSION, create=True)
    assert made is not None
    assert made.is_relative_to(real), f"created under the empty root: {made}"
