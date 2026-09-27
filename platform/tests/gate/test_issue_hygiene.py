"""The nightly issue sweep: duplicates closed only when the text agrees, and
the sidebar read from the labels.

  a title is not an        the older parser titled findings by their CWE class,
    identity                 so one title named several unrelated defects;
                             closing on the title alone would close real bugs

  a bundle is never        a Gitar review summary carries several findings;
    closed                   closing it as a duplicate of one of them would drop
                             the rest from the tracker

  a pathless report        joins a title's group only when that title names
                             exactly one file — the rule `locate` already uses

  the labels are the       Type, Priority and Effort are derived from them;
    source                   a type a person set is never overwritten
"""

from __future__ import annotations

import importlib.util
import sys

import pytest
from conftest import REPO_ROOT

SCRIPTS = REPO_ROOT / ".github" / "scripts"


@pytest.fixture
def hy(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "Atomz-org/data-platform")
    monkeypatch.setenv("DRY_RUN", "1")
    monkeypatch.syspath_prepend(str(SCRIPTS))
    for name in ("bot_findings", "issue_hygiene"):
        spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
        mod = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, name, mod)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
    return sys.modules["issue_hygiene"]


def issue(n: int, title: str, path: str, text: str, labels=(), fp: str = "") -> dict:
    head = f"### CodeRabbit — [`{path}:12`](https://x/{n})" if path else f"### Gitar — [PR #1](https://x/{n})"
    body = f"> Carried over.\n\n<!-- bot-finding:{fp or f'{n:016x}'} -->\n\n**Origin:** #1\n\n{head}\n\n{text}\n"
    return {"number": n, "title": title, "body": body, "labels": [{"name": x} for x in labels], "id": f"I_{n}"}


DEFECT = "The chain loader calls json loads on every line with no error handling so a torn line crashes verify"


def test_same_file_same_title_same_text_is_a_duplicate(hy) -> None:
    a = issue(10, "read_all() crashes", "pf/chain.py", DEFECT)
    b = issue(11, "read_all() crashes", "pf/chain.py", DEFECT + " entirely")
    [[(canon, _), (other, score)]] = hy.duplicate_groups([a, b])
    assert canon["number"] == 10 and other["number"] == 11 and score >= hy.SAME


def test_a_title_alone_is_not_an_identity(hy) -> None:
    """Two different defects, both titled by their CWE class, in one file."""
    a = issue(10, "Authorization Bypass (CWE-693)", "pf/x.py", "Bash can delete revoked json and the read fails open")
    b = issue(11, "Authorization Bypass (CWE-693)", "pf/x.py", "Re-raise Revoked before the broad handler in call")
    [[_, (_, score)]] = hy.duplicate_groups([a, b])
    assert score < hy.MAYBE
    assert hy.dedupe([a, b]) == set()


def test_different_files_are_different_defects(hy) -> None:
    a = issue(10, "Same title", "pf/a.py", DEFECT)
    b = issue(11, "Same title", "pf/b.py", DEFECT)
    assert hy.duplicate_groups([a, b]) == []


def test_a_pathless_restatement_joins_only_a_one_file_title(hy) -> None:
    a = issue(10, "Same title", "pf/a.py", DEFECT)
    p = issue(12, "Same title", "", DEFECT)
    assert [x["number"] for x, _ in hy.duplicate_groups([a, p])[0]] == [10, 12]
    b = issue(11, "Same title", "pf/b.py", DEFECT)
    groups = hy.duplicate_groups([a, b, p])
    assert all(12 not in [x["number"] for x, _ in g] for g in groups), "ambiguous: two files claim the title"


def test_a_bundle_is_flagged_never_closed(hy, monkeypatch: pytest.MonkeyPatch) -> None:
    a = issue(10, "Kill switch bypassed", "pf/base.py", DEFECT)
    bundle = issue(
        11, "Kill switch bypassed", "", "Code Review ⚠️ Changes requested 0 resolved / 3 findings\n\n" + DEFECT
    )
    flagged = []
    monkeypatch.setattr(hy, "flag_possible", lambda c, o, s: flagged.append(o["number"]))
    monkeypatch.setattr(hy, "close_duplicate", lambda c, o, s: pytest.fail("a bundle must not be closed"))
    assert hy.dedupe([a, bundle]) == set()
    assert flagged == [11]


def test_not_duplicate_keeps_a_pair_apart(hy) -> None:
    a = issue(10, "t", "pf/a.py", DEFECT)
    b = issue(11, "t", "pf/a.py", DEFECT, labels=["not-duplicate"])
    assert hy.duplicate_groups([a, b]) == []


def test_a_shared_fingerprint_is_a_duplicate_whatever_the_title(hy) -> None:
    a = issue(10, "old wording", "pf/a.py", "x", fp="aaaabbbbccccdddd")
    b = issue(11, "new wording", "pf/a.py", "y", fp="aaaabbbbccccdddd")
    [[_, (_, score)]] = hy.duplicate_groups([a, b])
    assert score == 1.0


# ----------------------------------------------------------------- sidebar --
def test_labels_are_back_filled_from_what_the_issue_says(hy) -> None:
    i = issue(
        20,
        "Leak",
        "pf/a.py",
        "_🔒 Security_ | _🟠 Major_ | _⚡ Quick win_\n\n**Leak**",
        labels=["bot-finding", "coderabbit", "severity:major", "security"],
    )
    hy.backfill_labels(i)
    have = hy.labels_of(i)
    assert {"priority:P0", "area:security-secrets", "effort:quick-win"} <= have


@pytest.mark.parametrize(
    "labels,want",
    [(["bug"], "Bug"), (["security"], "Bug"), (["documentation"], "Task"), ([], "Task")],
)
def test_type_follows_the_labels(hy, labels, want, capsys) -> None:
    hy.set_type(issue(21, "t", "a.py", "x", labels=labels), {})
    assert f"type → {want}" in capsys.readouterr().out


def test_a_type_a_person_set_stands(hy, capsys) -> None:
    hy.set_type(issue(22, "t", "a.py", "x", labels=["bug"]), {"issueType": {"name": "Feature"}})
    assert "type →" not in capsys.readouterr().out


def test_priority_and_effort_fields_follow_the_labels(hy, capsys) -> None:
    fields = {
        "Priority": {"id": "P", "options": [{"id": f"p{n}", "name": n} for n in ("Urgent", "High", "Medium", "Low")]},
        "Effort": {"id": "E", "options": [{"id": f"e{n}", "name": n} for n in ("High", "Medium", "Low")]},
    }
    hy.set_fields(issue(23, "t", "a.py", "x", labels=["priority:P0", "effort:heavy-lift"]), {}, fields)
    out = capsys.readouterr().out
    assert "Priority → Urgent" in out and "Effort → High" in out
    already = {
        "issueFieldValues": {
            "nodes": [{"name": "Urgent", "field": {"name": "Priority"}}, {"name": "High", "field": {"name": "Effort"}}]
        }
    }
    hy.set_fields(issue(23, "t", "a.py", "x", labels=["priority:P0", "effort:heavy-lift"]), already, fields)
    assert capsys.readouterr().out == "", "already right: nothing to write"
