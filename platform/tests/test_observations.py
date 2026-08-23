"""The observations-to-issues sync, driven end to end with a fake gh.

The script is repo tooling (.github/scripts), but its logic — which ledger row
wins, when an issue is filed, updated, left alone or closed — is platform
behaviour, so it is tested here with everything injected: a temporary ledger,
a fake gh runner, no network and no token.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / ".github" / "scripts"


@pytest.fixture
def lo(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    mod = importlib.import_module("loop_observations")
    importlib.reload(mod)
    mod.bf.REPO = "org/repo"
    mod.bf.PROJECT_TOKEN = ""          # board off; issues still tracked
    return mod


class FakeGH:
    """Records every gh call; answers `issue list` from a canned index."""

    def __init__(self, issues: list[dict] | None = None) -> None:
        self.issues = issues or []
        self.calls: list[list[str]] = []

    def __call__(self, cmd: list[str], token=None, check: bool = True) -> str:
        self.calls.append(cmd)
        if cmd[1:3] == ["issue", "list"]:
            return json.dumps(self.issues)
        if cmd[1:3] == ["issue", "create"]:
            return "https://github.com/org/repo/issues/41\n"
        return ""

    def of(self, *verb: str) -> list[list[str]]:
        return [c for c in self.calls if tuple(c[1:1 + len(verb)]) == verb]


def _row(loop: str, project: str, findings: list[str], group: str = "g",
         run_id: str = "r1", **extra) -> dict:
    return {"loop": loop, "group": group, "project": project, "run_id": run_id,
            "started_at": "2026-08-23T10:00:00+00:00", "outcome": "ok" if findings
            else "noop", "findings": findings, "level": "L1"} | extra


def test_latest_row_per_loop_project_wins_and_onboard_is_skipped(lo, tmp_path) -> None:
    (tmp_path / "loop-ledger.json").write_text(json.dumps([
        _row("pii-audit", "p", ["old finding"], run_id="r1"),
        _row("pii-audit", "p", [], run_id="r2"),
        _row("onboard-import", "p", ["ladder noise"]),
        _row("vendor-drift", "p", ["x moved"], outcome="circuit_open"),
    ]), encoding="utf-8")
    obs = lo.latest_observations(tmp_path)
    assert [(e["loop"], e["run_id"]) for e in obs] == [("pii-audit", "r2")]


def test_new_observation_files_one_labelled_issue(lo) -> None:
    gh = FakeGH()
    lo.GH = gh
    e = _row("pii-audit", "p", ["PII column `dim_x.email` reaches a mart"],
             suppressed=["known one"])
    lo.ensure_labels({e["loop"]})
    lo.upsert(e, lo.tracked(), board=None)
    create = gh.of("issue", "create")[0]
    body = create[create.index("--body") + 1]
    assert "<!-- loop-observation:pii-audit@g/p -->" in body
    assert "PII column" in body and "1 finding(s) suppressed" in body
    assert "loop:pii-audit" in create
    assert [c[3] for c in gh.of("label", "create")] == ["loop-observation", "loop:pii-audit"]


def test_unchanged_observation_touches_nothing(lo) -> None:
    e = _row("pii-audit", "p", ["same finding"])
    _, body = lo.render(e)
    gh = FakeGH([{"number": 7, "state": "OPEN", "title": "t", "body": body}])
    lo.GH = gh
    lo.upsert(e, lo.tracked(), board=None)
    assert not gh.of("issue", "create") and not gh.of("issue", "edit")


def test_changed_observation_edits_in_place_with_a_comment(lo) -> None:
    old = _row("pii-audit", "p", ["old finding"])
    _, old_body = lo.render(old)
    gh = FakeGH([{"number": 7, "state": "OPEN", "title": "t", "body": old_body}])
    lo.GH = gh
    lo.upsert(_row("pii-audit", "p", ["new finding"], run_id="r2"),
              lo.tracked(), board=None)
    assert not gh.of("issue", "create")
    edit = gh.of("issue", "edit")[0]
    assert edit[3] == "7" and "new finding" in edit[edit.index("--body") + 1]
    assert "r2" in gh.of("issue", "comment")[0][-1]


def test_clean_run_closes_the_open_issue_with_a_citation(lo) -> None:
    tracked_body = lo.render(_row("pii-audit", "p", ["was a finding"]))[1]
    gh = FakeGH([{"number": 9, "state": "OPEN", "title": "t", "body": tracked_body}])
    lo.GH = gh
    lo.close_clean(_row("pii-audit", "p", [], run_id="r9"), lo.tracked())
    assert gh.of("issue", "close")[0][3] == "9"
    assert "r9" in gh.of("issue", "comment")[0][-1]
    # A second clean run finds the issue CLOSED and does nothing.
    gh2 = FakeGH([{"number": 9, "state": "CLOSED", "title": "t", "body": tracked_body}])
    lo.GH = gh2
    lo.close_clean(_row("pii-audit", "p", []), lo.tracked())
    assert not gh2.of("issue", "close")


def test_proposals_appear_in_the_issue_body(lo) -> None:
    e = _row("test-failure-triage", "p", ["[HIGH] root_cause=model_logic: fix it"],
             proposals=[{"proposal_id": "abc", "status": "proposed",
                         "pr_url": "https://github.com/org/repo/pull/5"}])
    _, body = lo.render(e)
    assert "proposal `abc` **proposed** https://github.com/org/repo/pull/5" in body


def test_dry_run_needs_no_repo_and_calls_no_gh(lo, monkeypatch, capsys) -> None:
    monkeypatch.setattr(lo, "ROOT", Path("/nowhere/that/exists"))
    lo.bf.REPO = ""
    lo.main(["--dry-run"])                 # empty ledger -> prints and returns
    out = capsys.readouterr().out
    assert "no loop-ledger.json" in out
