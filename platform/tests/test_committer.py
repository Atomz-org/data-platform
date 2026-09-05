"""The committer: the model proposes, everything that matters is deterministic.

No test here talks to a model. The backend is the one untrusted input, so the
tests feed its worst outputs — invented paths, double assignment, wrapped
JSON — straight into the validation and parsing seams.
"""

from __future__ import annotations

import subprocess

import pytest
from pf import committer
from pf.committer import Change, PlannedCommit


def _git(root, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout


@pytest.fixture
def repo(tmp_path):
    """A scratch git repo with one commit and a real gate.yaml."""
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    (root / "a.py").write_text("print(1)\n")
    (root / "gate.yaml").write_text("version: 1\ndenylist:\n  - '.env'\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "init")
    return root


# ------------------------------------------------------------------ parsing --
def test_parse_strips_think_blocks_and_fences() -> None:
    reply = (
        '<think>hmm, two concerns here</think>\n```json\n{"commits": [{"message": "feat: x", "files": ["a.py"]}]}\n```'
    )
    plan = committer.parse_plan(reply)
    assert [p.subject for p in plan] == ["feat: x"]
    assert plan[0].files == ["a.py"]


def test_parse_bare_json_with_prose_around_it() -> None:
    reply = 'Here is the plan: {"commits": [{"message": "fix: y", "files": ["b"]}]} hope that helps!'
    assert committer.parse_plan(reply)[0].subject == "fix: y"


def test_parse_rejects_garbage_and_empty_plans() -> None:
    with pytest.raises(ValueError):
        committer.parse_plan("I could not decide.")
    with pytest.raises(ValueError):
        committer.parse_plan('{"commits": []}')


# --------------------------------------------------------------- validation --
def test_validate_catches_every_way_a_plan_lies(repo) -> None:
    changes = [
        Change(" M", "a.py"),
        Change("??", "b.py"),
        Change("??", ".env"),
        Change(" M", "vendor/thing"),
        Change("??", "c.py"),
    ]
    plan = [
        PlannedCommit(message="", files=["a.py", "ghost.py"]),
        PlannedCommit(message="feat: b", files=["b.py", "a.py", ".env", "vendor/thing"]),
        # c.py assigned nowhere
    ]
    problems = "\n".join(committer.validate_plan(plan, changes, repo))
    assert "empty message" in problems
    assert "ghost.py" in problems and "invented" in problems
    assert "assigned to both" in problems  # a.py twice
    assert "c.py" in problems and "no commit" in problems
    assert "vendor/thing" in problems and "human decision" in problems
    assert ".env" in problems and "gate-denied" in problems


def test_complete_plan_sweeps_what_the_model_forgot() -> None:
    changes = [Change(" M", "a.py"), Change("??", "b.py"), Change("??", "c.py")]
    plan = [PlannedCommit(message="feat: a and b", files=["a.py", "b.py"])]
    swept = committer.complete_plan(plan, changes)
    assert swept == ["c.py"]
    assert plan[-1].subject == committer.SWEEP_SUBJECT
    assert plan[-1].files == ["c.py"]
    # And a complete plan is left exactly alone.
    assert committer.complete_plan(plan, changes) == []
    assert len(plan) == 2


def test_vendor_pin_moves_are_invisible_to_the_survey(repo) -> None:
    # A path under vendor/ pending in the tree must not surface as a change —
    # committing it is refused anyway, so surfacing it deadlocks every plan.
    (repo / "vendor").mkdir()
    (repo / "vendor" / "pinned").write_text("x")
    (repo / "b.py").write_text("x = 2\n")
    assert [c.path for c in committer.changed_files(repo)] == ["b.py"]


def test_validate_accepts_a_complete_honest_plan(repo) -> None:
    changes = [Change(" M", "a.py"), Change("??", "b.py")]
    plan = [PlannedCommit(message="feat: split cleanly", files=["a.py", "b.py"])]
    assert committer.validate_plan(plan, changes, repo) == []


# ------------------------------------------------------------------- survey --
def test_changed_files_and_fingerprint_track_the_tree(repo) -> None:
    assert committer.changed_files(repo) == []
    before = committer.tree_fingerprint(repo)
    (repo / "b.py").write_text("x = 2\n")
    assert committer.changed_files(repo) == [Change("??", "b.py")]
    assert committer.tree_fingerprint(repo) != before
    # Our own scratch plan never appears as a pending change.
    committer.plan_path(repo).parent.mkdir(exist_ok=True)
    committer.plan_path(repo).write_text("{}")
    assert all(c.path != "data/commit_plan.json" for c in committer.changed_files(repo))


def test_saved_plan_dies_with_the_tree_it_described(repo) -> None:
    (repo / "b.py").write_text("x = 2\n")
    plan = [PlannedCommit(message="feat: b", files=["b.py"])]
    committer.save_plan(repo, plan, "test-model")
    loaded = committer.load_plan(repo)
    assert loaded is not None and loaded[1] == "test-model"
    (repo / "c.py").write_text("x = 3\n")  # the tree moved on
    assert committer.load_plan(repo) is None


# -------------------------------------------------------------------- apply --
def test_apply_commits_attributes_and_records(repo) -> None:
    from pf.provenance import ledger

    (repo / "a.py").write_text("print(2)\n")
    (repo / "b.py").write_text("x = 2\n")
    plan = [
        PlannedCommit(message="fix: a prints two", files=["a.py"]),
        PlannedCommit(message="feat: b exists\n\nBecause the test wants two commits.", files=["b.py"]),
    ]
    shas = committer.apply_plan(repo, plan, "qwen-test")
    assert len(shas) == 2
    assert committer.changed_files(repo) == [], "the tree must be clean afterwards"

    log = _git(repo, "log", "--format=%s", "-2")
    assert log.splitlines() == ["feat: b exists", "fix: a prints two"]
    body = _git(repo, "log", "-1", "--format=%B")
    assert "Commit-Split-By: qwen-test" in body

    recorded = ledger.actions(repo)
    ours = [r for r in recorded.values() if r["intent"].tool == "pf.committer"]
    assert len(ours) == 2
    for stages in ours:
        assert "execution" in stages, "every commit action must close"
        assert stages["execution"].payload["status"] == "ok"


def test_backend_selection_refuses_missing_claude(monkeypatch) -> None:
    monkeypatch.setattr(committer.shutil, "which", lambda _: None)
    with pytest.raises(RuntimeError, match="claude CLI not on PATH"):
        committer.backend("claude")
    # And the default is the local server, named after its model.
    be = committer.backend()
    assert be.name == committer.DEFAULT_MODEL


def test_local_backend_reads_env(monkeypatch) -> None:
    monkeypatch.setenv("PF_COMMIT_LLM_URL", "http://127.0.0.1:1234/v1/chat/completions")
    monkeypatch.setenv("PF_COMMIT_LLM_MODEL", "some/other-model")
    be = committer.LocalBackend()
    assert be.url.endswith(":1234/v1/chat/completions")
    assert be.name == "some/other-model"
