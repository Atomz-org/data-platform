"""Tests for the parts of the ontology flow that decide what is allowed to land.

Every case here is a hole that was open. An ontology whose rejections do not
stick is not governed, it is documented — and the difference only shows up much
later, as a class nobody approved sitting in the vocabulary every project is
validated against.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pf.ontology.annotate import (
    Annotation,
    from_proposal,
    load_annotations,
    load_unmodelled,
    merge_annotations,
)
from pf.ontology.model import load_ontology
from pf.ontology.proposal import Proposal, apply_to_extension
from pf.ontology.validate import validate_sources


def _proposal(axioms: list[dict]) -> Proposal:
    return Proposal(pid="p1", group="g", project="proj", source="scan",
                    created="2026-01-01", status="draft", axioms=axioms)


def _cls(name: str, table: str, accept: bool = True, identity: str = "id") -> dict:
    return {"kind": "class", "subject": name, "action": "add", "table": table,
            "identity": identity, "rows": 10, "accept": accept}


def _prop(subject: str, role: str, accept: bool = True) -> dict:
    return {"kind": "property", "subject": subject, "datatype": "string",
            "role": role, "accept": accept}


# --------------------------------------------------- rejection has to stick ----
def test_a_property_cannot_conjure_a_class_that_was_rejected(tmp_path: Path) -> None:
    """The hole this closes: an accepted `Supply.cost` created a class `Supply` —
    no label, no description, no identity — after the `Supply` class axiom had
    been rejected for having no unique key. The rejected term came back through
    the side door, minus everything that made it reviewable."""
    ext = tmp_path / "groups" / "g" / "ontology"
    ext.mkdir(parents=True)
    p = _proposal([
        _cls("Supply", "raw_supplies", accept=False, identity=""),
        _prop("Supply.cost", "money_amount", accept=True),
    ])
    path, applied = apply_to_extension(tmp_path, p)
    doc = yaml.safe_load(path.read_text())
    assert "Supply" not in (doc.get("classes") or {})
    assert applied["properties"] == 0


def test_a_relation_needs_both_of_its_classes(tmp_path: Path) -> None:
    (tmp_path / "groups" / "g" / "ontology").mkdir(parents=True)
    p = _proposal([
        _cls("Shipment", "raw_shipments"),
        {"kind": "relation", "subject": "shipment_refers_to_supplier",
         "domain": "Shipment", "range": "Supplier",
         "cardinality": "MANY_TO_ONE", "accept": True},
    ])
    path, applied = apply_to_extension(tmp_path, p)
    assert applied["relations"] == 0
    assert "not approved" in " ".join(
        yaml.safe_load(path.read_text())["_skipped_on_last_approval"])


def test_a_property_on_an_existing_platform_class_still_lands(tmp_path: Path) -> None:
    """The guard must not block the ordinary case: a proposal that only extends a
    class the platform ontology already defines."""
    (tmp_path / "groups" / "g" / "ontology").mkdir(parents=True)
    existing = next(iter(load_ontology().classes))
    _, applied = apply_to_extension(
        tmp_path, _proposal([_prop(f"{existing}.loyalty_tier", "status_enum")]))
    assert applied["properties"] == 1


def test_skips_are_recorded_in_the_file_not_only_on_the_terminal(tmp_path: Path) -> None:
    """They were written to the dict after it had already been serialised, so
    every reason an axiom did not land was printed once and thrown away."""
    (tmp_path / "groups" / "g" / "ontology").mkdir(parents=True)
    path, _ = apply_to_extension(tmp_path, _proposal([
        _cls("Supply", "raw_supplies", accept=False, identity=""),
        _prop("Supply.cost", "money_amount"),
    ]))
    assert yaml.safe_load(path.read_text())["_skipped_on_last_approval"]


# ------------------------------------------------ annotations from a scan ----
def test_only_accepted_axioms_become_annotations() -> None:
    """An annotation asserts that a column plays a role in the shared vocabulary.
    If the axiom behind it was rejected, the assertion has no backing."""
    anns = from_proposal(_proposal([
        _cls("Order", "raw_orders"),
        _cls("Ghost", "raw_ghost", accept=False),
        _prop("Order.total", "money_amount"),
        _prop("Order.secret", "pii_email", accept=False),
    ]))
    assert [a.resource for a in anns] == ["raw_orders"]
    assert "secret" not in anns[0].roles


def test_unapproved_relations_leave_links_empty() -> None:
    """A relation still called `refers_to` is a placeholder. Links fill in as
    they are named and approved, which is the correct order, not a limitation."""
    anns = from_proposal(_proposal([
        _cls("Order", "raw_orders"),
        {"kind": "relation", "subject": "order_refers_to_customer",
         "domain": "Order", "range": "Customer", "via": "customer_id",
         "cardinality": "MANY_TO_ONE", "accept": False},
    ]))
    assert anns[0].links == {}


def test_currency_is_stamped_only_where_money_needs_one() -> None:
    """Stamping a denomination on a resource with no money column asserts
    something about nothing."""
    anns = {a.resource: a for a in from_proposal(_proposal([
        _cls("Order", "raw_orders"),
        _prop("Order.total", "money_amount"),
        _cls("Store", "raw_stores"),
        _prop("Store.name", "label"),
    ]), currency="USD")}
    assert anns["raw_orders"].currency == "USD"
    assert anns["raw_stores"].currency == ""


def test_merge_never_overwrites_a_hand_written_annotation(tmp_path: Path) -> None:
    """An existing entry is a decision someone made. A generator you cannot
    re-run safely is one people stop running."""
    p = tmp_path / "annotations.yaml"
    merge_annotations(p, [Annotation(resource="raw_orders", concept="Order",
                                     description="mine", grain="one order")])
    added, kept = merge_annotations(
        p, [Annotation(resource="raw_orders", concept="Order", description="generated"),
            Annotation(resource="raw_new", concept="Product")])
    assert (added, kept) == (1, 1)
    assert {a.resource: a.description for a in load_annotations(p)}["raw_orders"] == "mine"


# ---------------------------------------------------- money and denomination ----
def test_money_with_no_denomination_anywhere_is_still_an_error() -> None:
    issues = validate_sources([Annotation(
        resource="r", concept="Order", roles={"id": "natural_key", "total": "money_amount"})])
    assert any(i.rule == "money-without-currency" for i in issues)


def test_a_declared_constant_currency_satisfies_the_rule() -> None:
    """Most single-currency sources carry no currency column. The old rule left
    them annotating a column that does not exist, or dropping the role and losing
    currency normalisation entirely."""
    issues = validate_sources([Annotation(
        resource="r", concept="Order", currency="USD",
        roles={"id": "natural_key", "total": "money_amount"})])
    assert not [i for i in issues if i.severity == "error"]


def test_a_currency_that_is_not_a_code_is_rejected() -> None:
    issues = validate_sources([Annotation(
        resource="r", concept="Order", currency="dollars",
        roles={"id": "natural_key", "total": "money_amount"})])
    assert any(i.rule == "unknown-currency" for i in issues)


def test_currency_survives_a_write_and_read(tmp_path: Path) -> None:
    p = tmp_path / "a.yaml"
    merge_annotations(p, [Annotation(resource="r", concept="Order", currency="EUR")])
    assert load_annotations(p)[0].currency == "EUR"


# ------------------------------------------------------ deliberate omission ----
def test_unmodelled_needs_a_reason_to_count(tmp_path: Path) -> None:
    """A reason string is the whole mechanism: it costs a line, and it converts
    'we forgot' into 'we decided'."""
    p = tmp_path / "a.yaml"
    p.write_text(yaml.safe_dump({
        "resources": [],
        "unmodelled": {"raw_bridge": "junction table, not an entity", "raw_x": "  "},
    }))
    assert load_unmodelled(p) == {"raw_bridge": "junction table, not an entity"}


def test_unmodelled_survives_a_regeneration(tmp_path: Path) -> None:
    p = tmp_path / "a.yaml"
    p.write_text(yaml.safe_dump({"resources": [], "unmodelled": {"raw_bridge": "why"}}))
    merge_annotations(p, [Annotation(resource="raw_orders", concept="Order")])
    assert load_unmodelled(p) == {"raw_bridge": "why"}
