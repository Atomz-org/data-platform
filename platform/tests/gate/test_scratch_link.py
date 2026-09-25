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
    for kind, _path, target, _owner in w._pairs(_session(home, root), root, create=True):
        assert target.is_relative_to(root), f"{kind} points outside the repo: {target}"


def test_the_scratch_directories_are_all_covered(harness) -> None:
    root, home = harness
    kinds = {k for k, *_ in w._pairs(_session(home, root), root, create=True)}
    assert set(w.SCRATCH_KINDS) <= kinds
    assert {"runs", "scripts"} <= kinds, "the existing workflow links must survive"


def test_an_empty_session_links_cleanly(harness) -> None:
    """The ordinary SessionStart path: nothing written yet, so nothing to adopt."""
    root, home = harness
    sess = _session(home, root)
    reports = w.link(root, home, session_dir=sess, create=True)
    scratch = {r.kind: r for r in reports if r.kind in w.SCRATCH_KINDS}
    assert set(scratch) == set(w.SCRATCH_KINDS)
    for kind, r in scratch.items():
        assert r.ok, f"{kind}: {r.state} {r.note}"
        assert r.path.is_symlink(), f"{kind} was not replaced by a link"
        assert r.path.resolve().is_relative_to(root)


def test_linking_twice_changes_nothing(harness) -> None:
    root, home = harness
    sess = _session(home, root)
    w.link(root, home, session_dir=sess, create=True)
    again = [r for r in w.link(root, home, session_dir=sess, create=True) if r.kind in w.SCRATCH_KINDS]
    assert [r.state for r in again] == ["linked"] * len(w.SCRATCH_KINDS)


def test_a_file_written_through_the_link_lands_in_the_repo(harness) -> None:
    """End to end, because that is the claim being made to the operator."""
    root, home = harness
    sess = _session(home, root)
    w.link(root, home, session_dir=sess, create=True)
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
    w.link(root, home, session_dir=sess, create=True)
    tmp = w.scratch_session(w.slug(root), SESSION)
    assert tmp is not None
    elsewhere = root.parent / "elsewhere"
    elsewhere.mkdir()
    (tmp / "scratchpad").unlink()
    (tmp / "scratchpad").symlink_to(elsewhere)
    report = next(r for r in w.link(root, home, session_dir=sess, create=True) if r.kind == "scratchpad")
    assert report.state == "refused"
    assert "already a link" in report.note


def test_creation_prefers_the_root_this_repo_already_uses(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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


# -------------------------------------------------------------- adoption ----
#
# SessionStart does not only fire on a new session. It fires again on resume, on
# clear and on every compact, by which point the harness has filled these
# directories. Refusing a populated one left a long session writing outside the
# repo for the rest of its life -- so the hook adopts, with one exception that
# was found the hard way.


def _populated(harness) -> tuple[Path, Path, Path]:
    """A session whose scratch directories exist already, as they do by the time
    a compaction fires the hook for the second time."""
    root, home = harness
    tmp = w.scratch_session(w.slug(root), SESSION, create=True)
    assert tmp is not None
    for kind in w.SCRATCH_KINDS:
        (tmp / kind).mkdir(parents=True, exist_ok=True)
    return root, home, tmp


def _report(root: Path, home: Path, kind: str, **kw) -> w.LinkReport:
    reports = w.link(root, home, session_dir=_session(home, root), create=True, **kw)
    return next(r for r in reports if r.kind == kind)


def test_a_directory_left_in_the_scratchpad_is_adopted(harness) -> None:
    """A scratchpad holds directories as readily as files -- a probe with a test
    beside it, a repository someone cloned to read. One such directory used to
    refuse the whole kind, because adoption is all or nothing: a directory that
    does not empty cannot be replaced by a link."""
    root, home, tmp = _populated(harness)
    (tmp / "scratchpad" / "probe").mkdir()
    (tmp / "scratchpad" / "probe" / "t.mjs").write_text("ok", encoding="utf-8")

    report = _report(root, home, "scratchpad", adopt=True)

    assert report.ok, f"{report.state}: {report.note}"
    landed = root / w.SCRATCH_DIR / SESSION / "scratchpad" / "probe" / "t.mjs"
    assert landed.read_text(encoding="utf-8") == "ok"
    assert (tmp / "scratchpad").is_symlink()


def test_a_link_the_harness_left_moves_without_being_followed(harness) -> None:
    """The harness links a task's output at the agent transcript it came from, so
    the directory being adopted legitimately holds links out of it. Copying what
    one points at is not this command's call; moving the link is, and an absolute
    link means the same file from its new home."""
    root, home, tmp = _populated(harness)
    outside = root.parent / "agent-1.jsonl"
    outside.write_text('{"agent":1}\n', encoding="utf-8")
    (tmp / "scratchpad" / "a.output").symlink_to(outside)

    report = _report(root, home, "scratchpad", adopt=True)

    assert report.ok, f"{report.state}: {report.note}"
    moved = root / w.SCRATCH_DIR / SESSION / "scratchpad" / "a.output"
    assert moved.is_symlink(), "the link was followed and copied, not moved"
    assert moved.readlink() == outside
    assert moved.read_text(encoding="utf-8") == '{"agent":1}\n'


def test_a_relative_link_is_refused_rather_than_repointed(harness) -> None:
    """Moving a relative link changes what it means. That is a refusal, not a
    move done quietly."""
    root, home, tmp = _populated(harness)
    (tmp / "scratchpad" / "sibling.txt").write_text("x", encoding="utf-8")
    (tmp / "scratchpad" / "rel").symlink_to(Path("sibling.txt"))

    report = _report(root, home, "scratchpad", adopt=True)

    assert report.state == "refused"
    assert "repoint" in report.note


def test_the_tasks_directory_is_left_alone_while_the_session_runs(harness) -> None:
    """The exception, and the reason `live` exists.

    Claude Code notes the tasks directory when a session starts and checks it
    again for every tool call. Finding it moved, or replaced by a link, it
    refuses to swap the output file into place -- and no command's output reaches
    the model again until the session restarts. Adopting this one from a hook
    trades a tidy directory for a session that cannot see.
    """
    root, home, tmp = _populated(harness)
    for kind in w.SCRATCH_KINDS:
        (tmp / kind / "already-here.output").write_text("x", encoding="utf-8")

    reports = {
        r.kind: r for r in w.link(root, home, session_dir=_session(home, root), create=True, adopt=True, live=True)
    }

    assert reports["tasks"].state == "refused"
    assert "while the session runs" in reports["tasks"].note
    assert not (tmp / "tasks").is_symlink(), "the running session lost its tasks dir"
    assert (tmp / "tasks" / "already-here.output").is_file()
    # The others are unaffected: one kind's refusal must not hold back the rest.
    for kind in ("scratchpad", "images"):
        assert reports[kind].ok, f"{kind}: {reports[kind].state} {reports[kind].note}"
        assert (tmp / kind).is_symlink()


def test_the_tasks_directory_is_adopted_once_nothing_is_running(harness) -> None:
    """`pf workflow link --adopt` is a person between sessions, not a hook."""
    root, home, tmp = _populated(harness)
    (tmp / "tasks" / "b1.output").write_text("output", encoding="utf-8")

    report = _report(root, home, "tasks", adopt=True)

    assert report.ok, f"{report.state}: {report.note}"
    landed = root / w.SCRATCH_DIR / SESSION / "tasks" / "b1.output"
    assert landed.read_text(encoding="utf-8") == "output"
    assert (tmp / "tasks").is_symlink()


def test_an_empty_tasks_directory_is_left_in_place_while_live(harness) -> None:
    """Empty is no exception (SC-6). The harness notes `tasks/` before
    SessionStart fires, so linking even an empty one from the hook cost a new
    session every command's output on 2026-09-25. It stays put, and the note
    names the two ways to keep it in the checkout instead."""
    root, home, tmp = _populated(harness)

    report = _report(root, home, "tasks", adopt=True, live=True)

    assert report.state == "refused", f"{report.state}: {report.note}"
    assert not (tmp / "tasks").is_symlink()
    assert "just claude" in report.note and "--adopt" in report.note


# ------------------------------------------------- CLAUDE_CODE_TMPDIR ----
#
# The durable form of everything above. Redirecting a directory after the
# harness made it is recovery; telling the harness where to put it is the rule.
# Claude Code reads CLAUDE_CODE_TMPDIR for its temp root and names it in the
# error it prints when that root is not where it left it.


def test_the_harness_variable_outranks_every_other_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """It is the only entry in `_tmp_roots` that is an interface rather than a
    convention, so a session that sets it must not be found somewhere else."""
    picked = tmp_path / "inside-the-repo"
    picked.mkdir()
    monkeypatch.setenv("CLAUDE_CODE_TMPDIR", str(picked))
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    assert w._tmp_roots()[0] == picked.resolve()


def test_an_unexpanded_variable_is_not_treated_as_a_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A settings `env` block writing `${CLAUDE_PROJECT_DIR}/.tmp` reaches a
    subprocess verbatim when nothing expands it. Resolved against the working
    directory that becomes a real root named after the variable, ranked ahead of
    the one the harness actually uses -- a session folder created where nothing
    ever looks. A value nobody expanded is a misconfiguration, not a path."""
    monkeypatch.setenv("CLAUDE_CODE_TMPDIR", "${CLAUDE_PROJECT_DIR}/.tmp")
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    roots = w._tmp_roots()
    assert all("$" not in str(r) for r in roots), roots
    assert roots[0] == tmp_path.resolve()


def test_a_session_already_inside_the_repo_is_left_alone(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """With CLAUDE_CODE_TMPDIR pointed at `<repo>/.tmp` the harness writes into
    the checkout directly. There is no directory to redirect, and linking one
    place in the repo at another would add a hop, a second place to look, and a
    link to keep correct -- for a property that already holds."""
    import os

    root = tmp_path / "repo"
    (root / ".git").mkdir(parents=True)
    home = tmp_path / "claude"
    sess = home / "projects" / w.slug(root) / SESSION
    sess.mkdir(parents=True)
    monkeypatch.setenv("CLAUDE_CODE_TMPDIR", str(root / ".tmp"))
    inside = root / ".tmp" / f"claude-{os.getuid()}" / w.slug(root) / SESSION
    (inside / "scratchpad").mkdir(parents=True)
    (inside / "scratchpad" / "note.md").write_text("already here", encoding="utf-8")

    report = next(r for r in w.link(root, home, session_dir=sess, adopt=True) if r.kind == "scratchpad")

    assert report.ok, f"{report.state}: {report.note}"
    assert not (inside / "scratchpad").is_symlink(), "a link was made for nothing"
    assert (inside / "scratchpad" / "note.md").is_file(), "the file was moved"
    assert (inside / "scratchpad").resolve().is_relative_to(root)


# ------------------------------------------------------------ the verdict ----
#
# SC-4 in docs/SESSION-CONTAINMENT.md. The failure this exists for is not a
# session writing outside the repo -- it is a session writing outside the repo
# that nobody notices, which is what actually happened: the link was refused,
# the refusal was printed once, and the repo's position stayed "contained" while
# the state was "outside".


def test_the_verdict_is_direct_when_nothing_needed_redirecting(harness) -> None:
    root, home = harness
    reports = w.link(root, home, session_dir=_session(home, root), create=True)
    fake = [r for r in reports if r.kind in w.SCRATCH_KINDS]
    # Rewrite the paths to where CLAUDE_CODE_TMPDIR would have put them.
    inside = [w.LinkReport(r.session, r.kind, root / ".tmp" / "s" / r.kind, r.target, "linked", "") for r in fake]
    state, lines = w.containment(root, inside)
    assert state == "direct", lines
    assert lines == ["files: .tmp/ (direct)"]


def test_the_verdict_is_linked_when_the_hook_had_to_redirect(harness) -> None:
    """The ordinary case today: bytes inside the repo, paths outside it."""
    root, home = harness
    reports = w.link(root, home, session_dir=_session(home, root), create=True)
    state, lines = w.containment(root, reports)
    assert state == "linked", lines
    assert lines == ["files: .tmp/ (linked)"]


def test_the_verdict_is_outside_and_counts_what_refused(harness) -> None:
    root, home = harness
    reports = w.link(root, home, session_dir=_session(home, root), create=True)
    broken = w.LinkReport(SESSION, "tasks", root / "x", root / "y", "refused", "holds 3 item(s)")
    state, lines = w.containment(root, [*reports, broken])
    assert state == "outside"
    assert any("OUTSIDE the repo" in ln for ln in lines)
    assert any("holds 3 item(s)" in ln for ln in lines)


def test_the_fix_is_offered_only_when_it_is_not_already_set(harness, monkeypatch: pytest.MonkeyPatch) -> None:
    """Advice that repeats when it has already been taken is noise, and an
    unexpanded `${...}` has not been taken however much it looks like it."""
    root, _ = harness
    broken = w.LinkReport(SESSION, "tasks", root / "x", root / "y", "refused", "no")

    monkeypatch.delenv("CLAUDE_CODE_TMPDIR", raising=False)
    assert any("just claude" in ln for ln in w.containment(root, [broken])[1])

    monkeypatch.setenv("CLAUDE_CODE_TMPDIR", "${CLAUDE_PROJECT_DIR}/.tmp")
    assert any("just claude" in ln for ln in w.containment(root, [broken])[1])

    monkeypatch.setenv("CLAUDE_CODE_TMPDIR", str(root / ".tmp"))
    assert not any("just claude" in ln for ln in w.containment(root, [broken])[1])


# --------------------------------------------------------------- capture ----
#
# What cannot be linked is copied. `subagents/`, `tool-results/` and the
# transcript live in the Claude Code folder, whose retention sweep walks
# directories with `readdir` -- which follows a symlink. A link there would put
# repo history behind a 30-day delete, so the repo takes a copy and the harness
# keeps its own.


def _session_with_files(tmp_path: Path) -> tuple[Path, Path, Path]:
    root = tmp_path / "repo"
    (root / ".git").mkdir(parents=True)
    home = tmp_path / "claude"
    sess = home / "projects" / w.slug(root) / SESSION
    (sess / "tool-results").mkdir(parents=True)
    (sess / "subagents").mkdir(parents=True)
    (sess.parent / f"{SESSION}.jsonl").write_text('{"turn":1}\n', encoding="utf-8")
    (sess / "tool-results" / "abc.txt").write_text("tool output", encoding="utf-8")
    (sess / "subagents" / "agent-1.jsonl").write_text('{"agent":1}\n', encoding="utf-8")
    return root, home, sess


def test_capture_brings_every_unlinkable_file_into_the_repo(tmp_path: Path) -> None:
    root, home, sess = _session_with_files(tmp_path)
    reports = w.capture(root, home, session_dir=sess)
    assert reports and all(r.ok for r in reports), [r.note for r in reports if not r.ok]
    here = root / w.SCRATCH_DIR / SESSION
    assert (here / "transcript.jsonl").read_text(encoding="utf-8") == '{"turn":1}\n'
    assert (here / "tool-results" / "abc.txt").read_text(encoding="utf-8") == "tool output"
    assert (here / "subagents" / "agent-1.jsonl").read_text(encoding="utf-8") == '{"agent":1}\n'
    for r in reports:
        assert r.dst.is_relative_to(root), f"captured outside the repo: {r.dst}"


def test_capture_never_removes_what_the_harness_still_owns(tmp_path: Path) -> None:
    """The harness is still using these files; only `link` ever moves anything."""
    root, home, sess = _session_with_files(tmp_path)
    w.capture(root, home, session_dir=sess)
    assert (sess.parent / f"{SESSION}.jsonl").is_file()
    assert (sess / "tool-results" / "abc.txt").is_file()
    assert (sess / "subagents" / "agent-1.jsonl").is_file()


def test_capturing_twice_copies_nothing_the_second_time(tmp_path: Path) -> None:
    root, home, sess = _session_with_files(tmp_path)
    w.capture(root, home, session_dir=sess)
    again = w.capture(root, home, session_dir=sess)
    assert {r.state for r in again} == {"current"}


def test_a_changed_file_is_captured_again(tmp_path: Path) -> None:
    root, home, sess = _session_with_files(tmp_path)
    w.capture(root, home, session_dir=sess)
    src = sess.parent / f"{SESSION}.jsonl"
    src.write_text('{"turn":1}\n{"turn":2}\n', encoding="utf-8")
    states = {r.dst.name: r.state for r in w.capture(root, home, session_dir=sess)}
    assert states["transcript.jsonl"] == "copied"
    assert states["abc.txt"] == "current"
    landed = root / w.SCRATCH_DIR / SESSION / "transcript.jsonl"
    assert landed.read_text(encoding="utf-8").count("turn") == 2


def test_a_linked_directory_is_not_copied_back_onto_itself(tmp_path: Path) -> None:
    """subagents/workflows is already a link into logs/; following it would copy
    the repo's own run history into a second place under .tmp/."""
    root, home, sess = _session_with_files(tmp_path)
    target = root / "logs" / "workflows"
    target.mkdir(parents=True)
    (target / "run.json").write_text("{}", encoding="utf-8")
    (sess / "subagents" / "workflows").symlink_to(target)
    names = {r.dst.name for r in w.capture(root, home, session_dir=sess)}
    assert "run.json" not in names
    assert not (root / w.SCRATCH_DIR / SESSION / "subagents" / "workflows").exists()


def test_listing_the_pairs_creates_nothing(harness) -> None:
    """`_pairs` is consulted by --check and by tests over throwaway repos. It
    created the temp directory it was about to report on, so a dry run changed
    the filesystem and a test linking a fake repo wrote into the real temp
    root. Creation is opt-in now; this is the case that caught it."""
    root, home = harness
    kinds = {k for k, *_ in w._pairs(_session(home, root), root)}
    assert kinds == {"runs", "scripts"}, "listing invented a scratch directory"
    assert w.scratch_session(w.slug(root), SESSION) is None


def test_a_dry_run_never_creates_even_when_asked_to(harness) -> None:
    """dry_run wins over create: --check reports, it does not arrange."""
    root, home = harness
    reports = w.link(root, home, session_dir=_session(home, root), dry_run=True, create=True)
    assert w.scratch_session(w.slug(root), SESSION) is None
    assert {r.kind for r in reports} == {"runs", "scripts"}
