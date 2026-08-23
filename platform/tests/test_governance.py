"""Tests for owner-editable governance.

The properties worth pinning are the ones that make the design defensible: that
an edit is auditable, that the comments explaining *why* a definition exists
survive the rewrite, and that an edit which cannot be made safely is refused
rather than made badly.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pf.governance import EditRejected, apply_edit, current, history, revert


@pytest.fixture()
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A repo root with one editable instance file and a tracking DB."""
    (tmp_path / "platform").mkdir()
    (tmp_path / "groups" / "acme" / "ontology").mkdir(parents=True)
    (tmp_path / "data").mkdir()
    (tmp_path / "groups" / "acme" / "ontology" / "instance.yaml").write_text(
        "# Why this group models these classes — the comment that must survive.\n"
        "group: acme\n"
        "domain: b2b_saas\n"
        "classes:\n"
        "  - Customer\n"
    , encoding="utf-8")
    return tmp_path


def test_an_edit_rewrites_the_file_and_records_who(repo: Path) -> None:
    row = apply_edit(repo, "instance", "domain", "fintech",
                     actor="owner@example.com", reason="we sell to banks now",
                     group="acme")
    assert row["applied"] is True
    assert current("instance", repo, "acme")["document"]["domain"] == "fintech"

    logged = history(repo)
    assert len(logged) == 1
    assert logged[0]["actor"] == "owner@example.com"
    assert logged[0]["reason"] == "we sell to banks now"


def test_the_comment_survives_the_rewrite(repo: Path) -> None:
    """A dumper would strip this, and the comment is the reason the class exists."""
    apply_edit(repo, "instance", "domain", "fintech", actor="a", group="acme")
    text = (repo / "groups" / "acme" / "ontology" / "instance.yaml").read_text(encoding="utf-8")
    assert "the comment that must survive" in text


def test_a_structural_change_is_refused_rather_than_flattened(repo: Path) -> None:
    with pytest.raises(EditRejected, match="not a value"):
        apply_edit(repo, "instance", "classes", ["Customer", "Payment"],
                   actor="a", group="acme")


def test_an_unknown_path_is_refused_and_leaves_the_file_alone(repo: Path) -> None:
    before = (repo / "groups" / "acme" / "ontology" / "instance.yaml").read_text(encoding="utf-8")
    with pytest.raises(EditRejected, match="no such path"):
        apply_edit(repo, "instance", "nope", "x", actor="a", group="acme")
    assert (repo / "groups" / "acme" / "ontology" / "instance.yaml").read_text(encoding="utf-8") == before


def test_a_scoped_surface_without_a_group_is_refused(repo: Path) -> None:
    with pytest.raises(EditRejected, match="needs a group"):
        apply_edit(repo, "instance", "domain", "x", actor="a")


def test_revert_restores_the_previous_value_as_a_new_row(repo: Path) -> None:
    """History is append-only: undoing is a new fact, not a deleted one."""
    first = apply_edit(repo, "instance", "domain", "fintech",
                       actor="a", group="acme")
    revert(repo, first["id"], actor="b")

    assert current("instance", repo, "acme")["document"]["domain"] == "b2b_saas"
    logged = history(repo)
    assert len(logged) == 2
    assert logged[0]["reason"].startswith("revert of")


def test_the_yaml_stays_parseable_after_an_edit(repo: Path) -> None:
    apply_edit(repo, "instance", "domain", "fintech", actor="a", group="acme")
    doc = yaml.safe_load(
        (repo / "groups" / "acme" / "ontology" / "instance.yaml").read_text(encoding="utf-8"))
    assert doc["classes"] == ["Customer"]
    assert doc["group"] == "acme"


def test_history_is_empty_rather_than_raising_before_any_edit(repo: Path) -> None:
    assert history(repo) == []
