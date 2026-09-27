"""The review-findings tracker: every bot finding becomes an issue.

a burst is not lost    CodeRabbit posts a review as a review body plus
                         several inline comments within a second. The
                         workflow's per-PR concurrency keeps one running and
                         one pending run and cancels the rest, so a run that
                         filed only the comment in its own payload lost every
                         cancelled sibling. A comment event now reconciles the
                         whole pull request.

severity is read,      Advanced-Tier security findings put a provenance field
  not positioned         before the severity; the second field is not always
                         the severity.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
from conftest import REPO_ROOT

SCRIPT = REPO_ROOT / ".github" / "scripts" / "bot_findings.py"


@pytest.fixture
def bf(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "Atomz-org/data-platform")
    spec = importlib.util.spec_from_file_location("bot_findings", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    # Registered first: `@dataclass` resolves its module through sys.modules.
    monkeypatch.setitem(sys.modules, "bot_findings", mod)
    spec.loader.exec_module(mod)
    return mod


ADVANCED_TIER = """_🔒 Security & Privacy_ | _🛡️ Detected with Advanced Tier_ | _🟠 Major_ | _⚡ Quick win_

<!-- cr-reachability -->

**Authorization Bypass**

**Reachability:** External
**CWE:** [CWE-693](https://cwe.mitre.org/data/definitions/693.html)

**Git global options let a command skip the `--no-verify` guard.**
"""


def test_an_advanced_tier_finding_keeps_its_severity(bf) -> None:
    [f] = bf.parse(ADVANCED_TIER, "platform/src/pf/agenthook.py", 176, "coderabbitai[bot]", "u", 584)
    assert f.title == "Authorization Bypass"
    assert f.severity == "major", "the 🟠 Major field, not the provenance field in position 2"
    assert f.kind == "security"
    assert bf.priority(f) == "P0 — Critical", "a major security finding is P0"


@pytest.mark.parametrize(
    "head,severity",
    [
        ("_⚠️ Potential issue_ | _🔴 Critical_", "critical"),
        ("_🎯 Functional Correctness_ | _🟡 Minor_ | _⚡ Quick win_", "minor"),
        ("_🔒 Security & Privacy_ | _🛡️ Detected with Advanced Tier_ | _🔴 Critical_", "critical"),
    ],
)
def test_the_ordinary_headers_read_as_before(bf, head: str, severity: str) -> None:
    [f] = bf.parse(head + "\n\n**Something is wrong here**\n", "a.py", 1, "coderabbitai[bot]", "u", 1)
    assert f.severity == severity


@pytest.mark.parametrize("event", ["pull_request_review_comment", "pull_request_review", "issue_comment"])
def test_a_comment_event_reconciles_the_whole_pr(
    bf, event: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Whichever run in a burst survives must file the findings of the runs
    the concurrency group cancelled — so it reads the PR, not its payload."""
    payload = {
        "comment": {"user": {"login": "coderabbitai[bot]"}, "body": "irrelevant"},
        "pull_request": {"number": 584},
    }
    if event == "issue_comment":
        payload = {
            "comment": payload["comment"],
            "issue": {"number": 584, "pull_request": {"url": "https://api.github.com/x"}},
        }
    if event == "pull_request_review":
        payload = {"review": payload["comment"], "pull_request": {"number": 584}}
    ev = tmp_path / "event.json"
    ev.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv("GITHUB_EVENT_NAME", event)
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(ev))

    seen: list[int] = []
    monkeypatch.setattr(bf, "collect", lambda pr: seen.append(pr) or [])
    monkeypatch.setattr(bf, "track", lambda findings, board=None: None)
    monkeypatch.setattr(bf, "record_resolution", lambda pr, board: 0)
    monkeypatch.setattr(bf, "ensure_board", lambda: None)
    monkeypatch.setattr(bf, "wait_for_checks", lambda pr: pytest.fail("a comment event must not wait for CI"))

    assert bf.main() == 0
    assert seen == [584]


def test_a_comment_on_a_plain_issue_is_ignored(bf, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ev = tmp_path / "event.json"
    ev.write_text(json.dumps({"comment": {"user": {"login": "x"}}, "issue": {"number": 9}}), encoding="utf-8")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "issue_comment")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(ev))
    monkeypatch.setattr(bf, "collect", lambda pr: pytest.fail("not a pull request"))
    assert bf.main() == 0


# --------------------------------------------------------------- labels ----
def test_an_issue_carries_priority_area_and_effort(bf) -> None:
    """Priority lived only on the project board, which needs PROJECTS_TOKEN —
    without it every issue was filed with no priority at all."""
    [f] = bf.parse(ADVANCED_TIER, "platform/src/pf/agenthook.py", 176, "coderabbitai[bot]", "u", 584)
    labels = bf.labels_for(f)
    assert {"bot-finding", "coderabbit", "severity:major", "security"} <= set(labels)
    assert "priority:P0" in labels
    assert "area:security-secrets" in labels
    assert "effort:quick-win" in labels


def test_every_label_the_script_applies_exists(bf) -> None:
    """`gh issue create --label X` fails outright when X does not exist."""
    known = {name for name, _, _ in bf.LABELS}
    for sev in ("critical", "major", "minor"):
        for kind in ("security", "bug", "edge-case", "quality", "docs"):
            for path in ("a.py", "docs/x.md", ".github/scripts/y.py", "platform/tests/t.py", ""):
                for effort in ("", "quick-win", "heavy-lift"):
                    f = bf.Finding("CodeRabbit", path, 1, "a title long enough", sev, kind, "", "u", 1, effort=effort)
                    assert set(bf.labels_for(f)) <= known, bf.labels_for(f)


@pytest.mark.parametrize(
    "have,want,add,remove",
    [
        # a new issue's labels go on as they are
        (set(), ["priority:P1", "severity:major", "area:docs"], ["priority:P1", "severity:major", "area:docs"], []),
        # re-reported harder: raised, the lower one removed
        (
            {"priority:P2", "severity:minor"},
            ["priority:P0", "severity:major"],
            ["priority:P0", "severity:major"],
            ["priority:P2", "severity:minor"],
        ),
        # re-reported softer: left where it is
        ({"priority:P0", "severity:major"}, ["priority:P2", "severity:minor"], [], []),
        # two priorities from an older run collapse to the higher
        ({"priority:P1", "priority:P3"}, ["priority:P2"], [], ["priority:P3"]),
        # area and effort are set once
        ({"area:docs", "effort:heavy-lift"}, ["area:security-secrets", "effort:quick-win"], [], []),
    ],
)
def test_relabelling_only_ever_raises(bf, have, want, add, remove) -> None:
    got_add, got_remove = bf.relabel(set(have), want)
    assert sorted(got_add) == sorted(add) and sorted(got_remove) == sorted(remove)


def test_a_headerless_inline_comment_is_still_filed(bf) -> None:
    body = "**This loop never terminates when the queue is empty.**\n\nThe `while` has no exit."
    [f] = bf.parse(body, "a.py", 3, "coderabbitai[bot]", "u", 1)
    assert f.title == "This loop never terminates when the queue is empty" and f.severity == "minor"


def test_a_reply_in_a_thread_is_not_a_finding(bf) -> None:
    body = "**Confirmed — addressed in commit abc1234.**"
    assert bf.parse(body, "a.py", 3, "coderabbitai[bot]", "u", 1, reply=True) == []
