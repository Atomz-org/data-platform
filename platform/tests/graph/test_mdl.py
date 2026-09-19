"""MDL relationships: which marts join, derived from what a project declared.

The graphs here are built by hand so each case isolates one resolution rule.
The first case is the commodity group's real shape, which produced zero
relationships: the entity mart is plural (`dim_commodities`), and the naming
heuristic matched the fact (`fct_commodity_prices_daily`) instead, then dropped
the resulting self-join.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pf.kg.store import Edge, Node, open_graph
from pf.projections.mdl import build_manifest

EXTENSION = """
classes:
  Commodity:
    parent: Product
    identity: commodity_id
    properties:
      commodity_id: {datatype: string, role: natural_key, required: true}
  PriceObservation:
    parent: Event
    identity: quote_id
    properties:
      quote_id: {datatype: string, role: natural_key, required: true}
  ImportTariff:
    identity: tariff_id
    properties:
      tariff_id: {datatype: string, role: natural_key, required: true}
roles:
  unit_price: {datatype: decimal, review: distribution}
relations:
  - {name: price_observation_of_commodity, domain: PriceObservation,
     range: Commodity, cardinality: MANY_TO_ONE, inverse: is priced by}
  - {name: import_tariff_on_commodity, domain: ImportTariff,
     range: Commodity, cardinality: MANY_TO_ONE, inverse: is subject to}
"""


def _project(tmp_path: Path, group: str, extension: str | None) -> Path:
    (tmp_path / "platform").mkdir()
    gdir = tmp_path / "groups" / group
    (gdir / "ontology").mkdir(parents=True)
    if extension:
        (gdir / "ontology" / "extension.yaml").write_text(extension)
    pdir = gdir / "projects" / f"{group}-x"
    pdir.mkdir(parents=True)
    return pdir


def _mart(name: str, columns: dict[str, dict], concept: str = "") -> tuple[list, list]:
    props = {"schema": "main_marts", "grain": ""}
    if concept:
        props["concept"] = concept
    nodes = [Node(id=f"model:{name}", kind="Model", name=name, layer="marts", props=props)]
    edges = []
    for col, cprops in columns.items():
        nodes.append(Node(id=f"col:model:{name}.{col}", kind="Column", name=col,
                          layer="marts", props={"model": name, **cprops}))
        edges.append(Edge(src=f"model:{name}", dst=f"col:model:{name}.{col}",
                          kind="has_column"))
    return nodes, edges


def _relation(name: str) -> Node:
    return Node(id=f"relation:{name}", kind="Relation", name=name, layer="topology",
                props={"label": name, "inverse": "", "description": ""})


def _realises(table: str, fk: str, src: str, dst: str, relation: str,
              cardinality: str = "MANY_TO_ONE") -> tuple[Node, Edge]:
    col = Node(id=f"col:table:raw.{table}.{fk}", kind="Column", name=fk, layer="raw")
    return col, Edge(src=col.id, dst=f"relation:{relation}", kind="realises",
                     props={"from_concept": src, "to_concept": dst, "fk_column": fk,
                            "fk_table": table, "cardinality": cardinality})


def _write(pdir: Path, parts: list[tuple[list, list]]) -> None:
    nodes = [n for ns, _ in parts for n in ns]
    edges = [e for _, es in parts for e in es]
    with open_graph(pdir / "kg" / "graph.duckdb") as g:
        g.add_nodes(nodes)
        g.add_edges(edges)


FK = {"role": "foreign_key", "links_to": "Commodity"}
KEY = {"role": "natural_key"}


@pytest.fixture()
def commodity(tmp_path: Path) -> dict:
    pdir = _project(tmp_path, "commodity", EXTENSION)
    raw_col, realises = _realises("futures_prices", "commodity_id",
                                  "PriceObservation", "Commodity",
                                  "price_observation_of_commodity")
    _write(pdir, [
        ([_relation("price_observation_of_commodity"),
          _relation("import_tariff_on_commodity"), raw_col], [realises]),
        _mart("dim_commodities", {"commodity_id": KEY}, concept="Commodity"),
        _mart("fct_commodity_prices_daily",
              {"price_id": KEY, "commodity_id": FK, "close_price": {"role": "unit_price"}},
              concept="PriceObservation"),
        # Derived fact, no concept declared, still keyed on a commodity.
        _mart("fct_lot_values", {"lot_id": KEY, "commodity_id": FK}),
        # Fed by a dbt seed: no raw table, so no realises edge exists for it.
        _mart("fct_tariffs", {"tariff_id": KEY, "commodity_id": FK},
              concept="ImportTariff"),
        # One row per commodity, but not the entity and not a foreign key.
        _mart("rpt_board", {"commodity_id": KEY}),
    ])
    return build_manifest(pdir, "commodity", "commodity-x")


def _conditions(manifest: dict) -> dict[str, str]:
    return {r["condition"]: r["properties"]["pf.relation"]
            for r in manifest["relationships"]}


def test_a_plural_entity_is_found_from_its_declared_concept(commodity) -> None:
    rels = _conditions(commodity)
    assert rels["fct_commodity_prices_daily.commodity_id = dim_commodities.commodity_id"] \
        == "price_observation_of_commodity"


def test_every_mart_declaring_the_foreign_key_joins(commodity) -> None:
    assert "fct_lot_values.commodity_id = dim_commodities.commodity_id" in _conditions(commodity)


def test_a_declared_mart_binds_without_a_raw_table(commodity) -> None:
    rels = _conditions(commodity)
    assert rels["fct_tariffs.commodity_id = dim_commodities.commodity_id"] \
        == "import_tariff_on_commodity"


def test_no_self_join_and_no_join_from_a_non_foreign_key(commodity) -> None:
    conditions = _conditions(commodity)
    assert len(conditions) == 3
    assert not any(c.startswith("rpt_board") for c in conditions)
    assert all(r["models"][0] != r["models"][1] for r in commodity["relationships"])
    assert len({r["name"] for r in commodity["relationships"]}) == 3


def test_a_group_role_is_typed_from_the_group_ontology(commodity) -> None:
    fact = next(m for m in commodity["models"] if m["name"] == "fct_commodity_prices_daily")
    close = next(c for c in fact["columns"] if c["name"] == "close_price")
    assert close["type"] == "DECIMAL"


def test_a_project_that_declares_nothing_still_joins_by_name(tmp_path: Path) -> None:
    """acme's shape: no concepts, an undocumented FK found in the warehouse."""
    pdir = _project(tmp_path, "acme", None)
    raw_col, realises = _realises("charges", "customer_id", "Payment", "Customer",
                                  "customer_pays_payment")
    _write(pdir, [
        ([_relation("customer_pays_payment"), raw_col], [realises]),
        _mart("dim_customers", {"customer_id": KEY}),
        _mart("fct_payments", {"payment_id": KEY, "customer_id": {"role": "foreign_key"}}),
    ])
    manifest = build_manifest(pdir, "acme", "acme-x")
    assert _conditions(manifest) == {
        "fct_payments.customer_id = dim_customers.customer_id": "customer_pays_payment"}


def test_a_declared_column_without_a_type_takes_the_warehouse_type(tmp_path: Path) -> None:
    """Most yml columns name no data_type. The MDL used to type them VARCHAR,
    so a declared boolean flag became a string a BI filter compares against."""
    import duckdb
    from pf.kg.build import _add_physical_columns, mcol, mid
    from pf.kg.store import Node

    (tmp_path / "data").mkdir()
    con = duckdb.connect(str(tmp_path / "data" / "p.duckdb"))
    con.execute("create table fct_x (is_ok boolean, n integer)")
    con.close()
    flag = Node(id=mcol("fct_x", "is_ok"), kind="Column", name="is_ok", layer="marts",
                props={"role": "", "pii": False, "model": "fct_x", "data_type": None})
    nodes = [Node(id=mid("fct_x"), kind="Model", name="fct_x", layer="marts"), flag]
    _add_physical_columns(tmp_path, "p", nodes, [])
    assert {n.name: n.props["data_type"] for n in nodes if n.kind == "Column"} == {
        "is_ok": "BOOLEAN", "n": "INTEGER"}
    assert len(nodes) == 3  # the declared node was typed in place, not duplicated
