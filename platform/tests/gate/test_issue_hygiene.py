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


# ----------------------------------------------------------------- semantic --
class _FakeEmbedder:
    """Vectors by keyword, so a test can say which pairs are 'the same'."""

    name = "fake"

    def __init__(self, axes: dict[str, list[float]]) -> None:
        self.axes = axes

    def encode(self, texts: list[str]) -> list[list[float]]:
        out = []
        for t in texts:
            v = next((vec for key, vec in self.axes.items() if key in t.lower()), [0.0, 0.0, 1.0])
            out.append(v)
        return out


def test_semantic_pass_pairs_by_embedding_within_one_file(hy) -> None:
    emb = _FakeEmbedder({"torn line": [1.0, 0.0, 0.0], "unrelated": [0.0, 1.0, 0.0]})
    a = issue(20, "read_all() crashes", "pf/chain.py", "a torn line crashes verify")
    b = issue(21, "verify blows up on partial writes", "pf/chain.py", "a torn line crashes verify too")
    c = issue(22, "something unrelated", "pf/chain.py", "unrelated defect")
    d = issue(23, "read_all() crashes", "pf/other.py", "a torn line crashes verify")
    groups = hy.semantic_groups([a, b, c, d], emb)
    pairs = {(g[0][0]["number"], g[1][0]["number"]): g[1][1] for g in groups}
    assert pairs == {(20, 21): 1.0}, "same file, same meaning — and never across files"
    assert hy.duplicate_groups([a, b]) == [], "the lexical pass could not see this pair: titles differ"


def test_semantic_thresholds_close_or_flag(hy, monkeypatch) -> None:
    emb = _FakeEmbedder({"first": [1.0, 0.0, 0.0], "second": [0.8, 0.6, 0.0]})  # cosine 0.8
    a = issue(30, "first thing", "pf/x.py", "first defect")
    b = issue(31, "second thing", "pf/x.py", "second defect")
    closed_calls, flagged_calls = [], []
    monkeypatch.setattr(hy, "close_duplicate", lambda c, o, s: closed_calls.append((c["number"], o["number"], s)))
    monkeypatch.setattr(hy, "flag_possible", lambda c, o, s: flagged_calls.append((c["number"], o["number"], s)))
    assert hy.dedupe([a, b], emb) == set()
    assert closed_calls == [] and flagged_calls == [(30, 31, 0.8)], "0.8 is possible, not certain"
    monkeypatch.setattr(hy, "SEMANTIC_SAME", 0.7)
    assert hy.dedupe([a, b], emb) == {31}
    assert closed_calls == [(30, 31, 0.8)]


def test_not_duplicate_and_bundles_are_respected_by_the_semantic_pass(hy, monkeypatch) -> None:
    emb = _FakeEmbedder({"same": [1.0, 0.0, 0.0]})
    a = issue(40, "same one", "pf/x.py", "same defect")
    b = issue(41, "same two", "pf/x.py", "same defect", labels=("not-duplicate",))
    assert hy.semantic_groups([a, b], emb) == []
    c = issue(42, "same three", "", "same defect / 3 findings")
    closed = []
    monkeypatch.setattr(hy, "close_duplicate", lambda *x: closed.append(x))
    monkeypatch.setattr(hy, "flag_possible", lambda *x: None)
    assert hy.dedupe([a, c], emb) == set(), "a bundle is never closed"


def test_without_an_embedder_the_semantic_pass_is_empty(hy) -> None:
    a = issue(50, "x", "pf/x.py", "same defect")
    b = issue(51, "y", "pf/x.py", "same defect")
    assert hy.semantic_groups([a, b], None) == []
    assert hy.dedupe([a, b], None) == set()


def test_embedder_is_never_fatal(hy, monkeypatch) -> None:
    monkeypatch.setattr(hy, "EMBEDDINGS", "auto")
    monkeypatch.setattr(hy, "Embedder", lambda name: (_ for _ in ()).throw(ImportError("no torch")))
    assert hy.embedder() is None
    monkeypatch.setattr(hy, "EMBEDDINGS", "off")
    assert hy.embedder() is None


# ------------------------------------------------------- label -> field --
def test_labels_map_to_board_fields(hy) -> None:
    fv = hy.field_values({"priority:high", "effort:quick-win", "area:security", "loop-observation"})
    assert fv == {"Priority": "High", "Effort": "Low", "Category": "Security"}
    assert hy.field_values({"priority:P0"}) == {"Priority": "Urgent"}
    assert hy.field_values({"area:lineage"}) == {"Category": "Lineage"}, "an unlisted area still title-cases"
    assert hy.field_values({"bug"}) == {}
    assert hy.field_values({"priority:P1", "priority:P3"}) == {"Priority": "High"}, "deterministic when labels disagree"


def test_field_map_override_must_be_well_formed(hy, monkeypatch) -> None:
    monkeypatch.setenv("HYGIENE_LABEL_FIELDS", '{"Priority": {"sev:1": "Urgent"}}')
    assert hy.field_map() == {"Priority": {"sev:1": "Urgent"}}
    assert hy.field_values({"sev:1"}, hy.field_map()) == {"Priority": "Urgent"}
    monkeypatch.setenv("HYGIENE_LABEL_FIELDS", "not json")
    assert hy.field_map() == hy.DEFAULT_FIELD_MAP


def test_dry_run_sync_adds_nothing_to_the_board(hy, monkeypatch) -> None:
    def boom(*a, **k):
        raise AssertionError("a dry run must not touch the board")

    monkeypatch.setattr(hy.bf, "board_item", boom)
    monkeypatch.setattr(hy.bf, "set_fields", boom)
    issues = [issue(60, "a", "pf/x.py", "d", labels=("priority:high",)), issue(61, "b", "pf/x.py", "d")]
    assert hy.sync_label_fields(("PID", {}), issues) == 1
    assert hy.TALLY["synced"] and "Priority=High" in hy.TALLY["synced"][0]
    assert hy.sync_label_fields(None, issues) == 0


def test_live_sync_writes_the_mapped_fields(hy, monkeypatch) -> None:
    monkeypatch.setattr(hy, "DRY_RUN", False)
    written = []
    monkeypatch.setattr(hy.bf, "board_item", lambda board, n: f"ITEM{n}")
    monkeypatch.setattr(hy.bf, "set_fields", lambda board, item, want: written.append((item, want)))
    issues = [issue(70, "a", "pf/x.py", "d", labels=("priority:P2", "effort:heavy-lift"))]
    assert hy.sync_label_fields(("PID", {}), issues) == 1
    assert written == [("ITEM70", {"Priority": "Medium", "Effort": "High"})]
