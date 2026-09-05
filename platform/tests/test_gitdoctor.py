"""The git doctor: the model picks from a closed menu; the menu is the law.

As with the committer, no test talks to a model — the model's reply is the
untrusted input, so the tests feed the validation wall its worst versions:
off-menu remedies, invented remedy names, findings silently omitted.
"""

from __future__ import annotations

import subprocess

import pytest
from pf import gitdoctor
from pf.gitdoctor import Finding, Resolution


def _git(root, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout


def _mkrepo(path, filename="f.txt"):
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "-q")
    _git(path, "config", "user.email", "t@example.com")
    _git(path, "config", "user.name", "t")
    _git(path, "config", "protocol.file.allow", "always")
    (path / filename).write_text("1\n")
    _git(path, "add", "-A")
    _git(path, "commit", "-q", "-m", "init")
    return path


@pytest.fixture
def repo_with_drift(tmp_path):
    """A parent repo whose one submodule is checked out past its recorded pin."""
    upstream = _mkrepo(tmp_path / "upstream")
    parent = _mkrepo(tmp_path / "parent")
    _git(parent, "-c", "protocol.file.allow=always", "submodule", "add", str(upstream), "sub")
    _git(parent, "commit", "-q", "-m", "add sub")
    # Upstream moves; the checkout follows without the pin being updated.
    (upstream / "f.txt").write_text("2\n")
    _git(upstream, "commit", "-q", "-am", "move")
    sub = parent / "sub"
    _git(sub, "fetch", "-q", "origin")
    _git(sub, "checkout", "-q", "origin/HEAD" if False else "FETCH_HEAD")
    return parent


def test_diagnose_sees_pin_drift_and_stale_plan(repo_with_drift) -> None:
    from pf.committer import plan_path

    plan_path(repo_with_drift).parent.mkdir(exist_ok=True)
    plan_path(repo_with_drift).write_text(
        '{"fingerprint": "not-this-tree", "commits": [{"message": "x", "files": ["y"]}]}'
    )

    kinds = {f.kind for f in gitdoctor.diagnose(repo_with_drift)}
    assert "pin-drift" in kinds
    assert "stale-plan" in kinds


def test_validation_rejects_everything_off_menu() -> None:
    drift = Finding("pin-drift", "vendor/x", "d")
    dirty = Finding("dirty-submodule", "vendor/y", "d")
    problems = "\n".join(
        gitdoctor.validate_resolutions(
            [
                Resolution(drift, "deinit_nested", "wrong menu"),  # real remedy, wrong kind
                Resolution(dirty, "restore_pin", "dirty is leave-only"),
                Resolution(drift, "rm -rf", "invented"),
            ]
        )
    )
    assert "not on the menu for pin-drift" in problems
    assert "not on the menu for dirty-submodule" in problems
    assert "'rm -rf'" in problems


def test_omitted_findings_default_to_leave() -> None:
    findings = [Finding("pin-drift", "a", "d"), Finding("conflict", "b", "d")]
    reply = '{"resolutions": [{"finding": 0, "remedy": "restore_pin", "why": "drift"}]}'
    resolutions = gitdoctor.parse_resolutions(reply, findings)
    assert [r.remedy for r in resolutions] == ["restore_pin", "leave"]
    assert gitdoctor.validate_resolutions(resolutions) == []


def test_apply_restores_the_pin_and_records(repo_with_drift) -> None:
    from pf.provenance import ledger

    findings = gitdoctor.diagnose(repo_with_drift)
    drift = next(f for f in findings if f.kind == "pin-drift")
    done = gitdoctor.apply_resolutions(
        repo_with_drift, [Resolution(drift, "restore_pin", "unreviewed drift")], "qwen-test"
    )
    assert done == ["restore_pin: sub"]
    assert not any(f.kind == "pin-drift" for f in gitdoctor.diagnose(repo_with_drift))

    ours = [r for r in ledger.actions(repo_with_drift).values() if r["intent"].tool == "pf.gitdoctor"]
    assert len(ours) == 1
    assert ours[0]["execution"].payload["status"] == "ok"


def test_rulebook_reaches_the_model_verbatim() -> None:
    prompt = gitdoctor.build_prompt([Finding("pin-drift", "vendor/x", "drifted")])
    assert gitdoctor.RULEBOOK in prompt
    assert "[pin-drift] vendor/x" in prompt
    # The rulebook enumerates the hard prohibitions the menu cannot express.
    for phrase in ("--no-verify", "reset --hard", "provenance", "human decision"):
        assert phrase in gitdoctor.RULEBOOK
