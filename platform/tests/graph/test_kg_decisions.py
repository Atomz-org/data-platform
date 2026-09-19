"""Decisions (ADRs) in the graph, and what they change downstream of it.

`decisions/README.md` has promised "The knowledge graph indexes these, so
`kg_search` finds them" since the scaffold first wrote it. Before this the graph
never read the directory, so the promise was false in every project and nothing
noticed: a reviewer only misses an ADR they did not know to look for. These
cases pin the whole chain, from the file on disk to the impact report and the
card, because each link is the kind of thing that quietly stops working.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pf.kg.build import build_graph
from pf.kg.card import render_project_card
from pf.kg.impact import impact_of, impact_of_many
from pf.kg.query import kg_search
from pf.kg.store import open_graph

ADR = """# ADR-0001: Orders are gross

**Status:** accepted · 2026-01-02

## Decision

`fct_orders` carries the gross amount in `fct_orders.amount`, and `revenue`
is the sum of it. Refunds are a separate fact. `nothing_here` is a term this
project does not model, and `amount` on its own names half the warehouse.
"""

# Only the keys `_add_dbt` and `_add_semantic` read. A second model, never
# mentioned by the ADR, gives the negative cases a real node to ask about; it
# carries an `amount` of its own so the bare-column case has a wrong answer
# available to give.
MANIFEST = {
    "nodes": {
        "model.p.fct_orders": {
            "resource_type": "model", "name": "fct_orders",
            "path": "marts/fct_orders.sql", "description": "Orders",
            "columns": {"amount": {}},
        },
        "model.p.int_orders__clean": {
            "resource_type": "model", "name": "int_orders__clean",
            "path": "intermediate/int_orders__clean.sql",
            "columns": {"amount": {}},
        },
        "model.p.dim_dates": {
            "resource_type": "model", "name": "dim_dates",
            "path": "marts/dim_dates.sql", "columns": {},
        },
    },
    "parent_map": {"model.p.fct_orders": ["model.p.int_orders__clean"]},
}

SEMANTIC = {
    "semantic_models": [
        {"name": "orders", "node_relation": {"alias": "fct_orders"},
         "measures": [{"name": "order_amount"}], "dimensions": []},
    ],
    "metrics": [
        {"name": "revenue", "type": "simple", "label": "Revenue",
         "type_params": {"measure": {"name": "order_amount"}}},
    ],
}


def _project(tmp_path: Path, *, with_decision: bool = True) -> Path:
    root = tmp_path / "p"
    target = root / "transform" / "target"
    target.mkdir(parents=True)
    (target / "manifest.json").write_text(json.dumps(MANIFEST))
    (target / "semantic_manifest.json").write_text(json.dumps(SEMANTIC))
    if with_decision:
        (root / "decisions").mkdir()
        (root / "decisions" / "ADR-0001-orders-are-gross.md").write_text(ADR)
        (root / "decisions" / "README.md").write_text("# Decision log\n")
    return root


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = _project(tmp_path)
    build_graph(root, group="", project="p")
    return root


@pytest.fixture
def graph(project: Path) -> Path:
    return project / "kg" / "graph.duckdb"


# ------------------------------------------------------------------ node ----
def test_the_adr_is_a_node_with_its_title_status_and_date(graph: Path) -> None:
    with open_graph(graph, read_only=True) as g:
        node = g.node("decision:ADR-0001")
    assert node is not None
    assert node.kind == "Decision"
    assert node.name == "ADR-0001"
    assert node.layer == "governance"
    assert node.label == "Orders are gross"
    assert node.props == {"status": "accepted", "date": "2026-01-02",
                          "path": "decisions/ADR-0001-orders-are-gross.md"}


def test_a_project_without_a_decision_log_builds_with_no_decision_nodes(tmp_path: Path) -> None:
    root = _project(tmp_path, with_decision=False)
    counts = build_graph(root, group="", project="p")
    assert "Decision" not in counts
    assert counts["Model"] == 3


# ----------------------------------------------------------------- edges ----
def test_decides_edges_reach_the_model_its_column_and_the_metric(graph: Path) -> None:
    """Direction is the store's contract: the decision is upstream of what it
    governs, so it never shows up as a dependant."""
    with open_graph(graph, read_only=True) as g:
        out = g.out_edges("decision:ADR-0001")
        assert g.in_edges("decision:ADR-0001") == []
    assert all(e.kind == "decides" for e in out)
    assert {e.dst for e in out} == {
        "model:fct_orders", "col:model:fct_orders.amount", "metric:revenue",
    }


def test_unknown_terms_and_bare_column_names_link_nothing(graph: Path) -> None:
    """`amount` alone is a column on half the warehouse. Linking it would make
    one decision appear to govern every model that has one."""
    with open_graph(graph, read_only=True) as g:
        dsts = {e.dst for e in g.out_edges("decision:ADR-0001")}
    assert not any("nothing_here" in d for d in dsts)
    assert "col:model:int_orders__clean.amount" not in dsts
    assert not any(d.endswith(".amount") and "fct_orders" not in d for d in dsts)


# Two semantic models exposing the same dimension name, as a conformed
# `price_date` is on every fact in a group. `dim_dates` stands in for the
# second fact; only the semantic layer is asked about here.
SEMANTIC_SHARED_DIM = {
    "semantic_models": [
        {"name": "orders", "node_relation": {"alias": "fct_orders"},
         "measures": [{"name": "order_amount"}],
         "dimensions": [{"name": "order_date", "type": "time"}]},
        {"name": "dates", "node_relation": {"alias": "dim_dates"},
         "measures": [],
         "dimensions": [{"name": "order_date", "type": "time"}]},
    ],
    "metrics": [],
}

ADR_BARE_DIM = """# ADR-0002: Dates are UTC

**Status:** accepted · 2026-01-03

`order_date` is midnight UTC wherever it is exposed.
"""

ADR_ONE_DIM = """# ADR-0003: Order dates are the checkout day

**Status:** accepted · 2026-01-04

`orders.order_date` is the checkout day, not the settlement day.
"""


def _decides(graph: Path, decision: str) -> set[str]:
    with open_graph(graph, read_only=True) as g:
        return {e.dst for e in g.out_edges(decision)}


def test_a_bare_dimension_name_reaches_every_semantic_model_that_exposes_it(
        tmp_path: Path) -> None:
    """A dimension name recurs once per semantic model on purpose: it is the
    conformed vocabulary, and a decision about it governs every copy."""
    root = _project(tmp_path)
    (root / "transform" / "target" / "semantic_manifest.json").write_text(
        json.dumps(SEMANTIC_SHARED_DIM))
    (root / "decisions" / "ADR-0002-dates-are-utc.md").write_text(ADR_BARE_DIM)
    build_graph(root, group="", project="p")
    assert _decides(root / "kg" / "graph.duckdb", "decision:ADR-0002") == {
        "dim:orders__order_date", "dim:dates__order_date",
    }


def test_a_qualified_dimension_reaches_one_semantic_model_only(tmp_path: Path) -> None:
    """`semantic_model.dimension` is the precise form, as `model.column` is for
    a column: a decision about one fact's copy must not appear on the other."""
    root = _project(tmp_path)
    (root / "transform" / "target" / "semantic_manifest.json").write_text(
        json.dumps(SEMANTIC_SHARED_DIM))
    (root / "decisions" / "ADR-0003-checkout-day.md").write_text(ADR_ONE_DIM)
    build_graph(root, group="", project="p")
    assert _decides(root / "kg" / "graph.duckdb", "decision:ADR-0003") == {
        "dim:orders__order_date",
    }


# ---------------------------------------------------------------- search ----
def test_kg_search_finds_the_decision_by_number_and_by_title(graph: Path) -> None:
    assert "decision:ADR-0001" in kg_search(graph, "ADR-0001")
    assert "decision:ADR-0001" in kg_search(graph, "gross")


# ---------------------------------------------------------------- impact ----
def test_impact_names_the_decision_a_change_re_opens(graph: Path) -> None:
    report = impact_of(graph, "model:fct_orders")
    assert [n.id for n in report.decisions] == ["decision:ADR-0001"]
    rendered = report.render()
    assert "Decisions to re-read (1):" in rendered
    assert "ADR-0001 — Orders are gross" in rendered
    assert report.to_dict()["decisions"][0]["id"] == "decision:ADR-0001"


def test_a_decision_upstream_of_the_root_is_reached_through_its_dependants(graph: Path) -> None:
    """int_orders__clean feeds fct_orders; the ADR is about fct_orders. Changing
    the intermediate model still re-opens it."""
    report = impact_of(graph, "model:int_orders__clean")
    assert [n.id for n in report.decisions] == ["decision:ADR-0001"]


def test_a_node_no_decision_mentions_has_none(graph: Path) -> None:
    report = impact_of(graph, "model:dim_dates")
    assert report.decisions == []
    assert "Decisions" not in report.render()


def test_a_safe_change_still_lists_the_decision_it_contradicts(graph: Path) -> None:
    """Nothing depends on the metric, so the change is safe. It is still the
    thing the ADR was written about."""
    report = impact_of(graph, "metric:revenue")
    assert report.total == 0
    assert report.severity == "safe"
    rendered = report.render()
    assert "Safe to change" in rendered
    assert "Decisions to re-read (1):" in rendered


def test_severity_ignores_decisions(graph: Path) -> None:
    """A decision changes what a reviewer reads, never whether the gate fails."""
    assert impact_of(graph, "metric:revenue").severity == "safe"
    assert impact_of(graph, "model:dim_dates").severity == "safe"


def test_a_change_set_merges_decisions_once(graph: Path) -> None:
    report = impact_of_many(graph, ["model:fct_orders", "model:int_orders__clean"])
    assert [n.id for n in report.decisions] == ["decision:ADR-0001"]
    assert len(report.to_dict()["decisions"]) == 1


# ------------------------------------------------------------------ card ----
def test_the_card_lists_decisions_and_intermediate_models(project: Path) -> None:
    text = render_project_card(project, "g", "p").read_text()
    assert "**Intermediate models (1):** `int_orders__clean`" in text
    assert "**Decisions (1):**" in text
    assert "- `ADR-0001` — Orders are gross" in text


def test_the_card_omits_the_sections_when_there_is_nothing_to_say(tmp_path: Path) -> None:
    root = _project(tmp_path, with_decision=False)
    manifest = dict(MANIFEST)
    manifest["nodes"] = {k: v for k, v in MANIFEST["nodes"].items() if "int_" not in k}
    manifest["parent_map"] = {}
    (root / "transform" / "target" / "manifest.json").write_text(json.dumps(manifest))
    build_graph(root, group="", project="p")
    text = render_project_card(root, "g", "p").read_text()
    assert "Decisions" not in text
    assert "Intermediate models" not in text
