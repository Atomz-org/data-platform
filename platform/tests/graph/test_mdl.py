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
        nodes.append(
            Node(id=f"col:model:{name}.{col}", kind="Column", name=col, layer="marts", props={"model": name, **cprops})
        )
        edges.append(Edge(src=f"model:{name}", dst=f"col:model:{name}.{col}", kind="has_column"))
    return nodes, edges


def _relation(name: str) -> Node:
    return Node(
        id=f"relation:{name}",
        kind="Relation",
        name=name,
        layer="topology",
        props={"label": name, "inverse": "", "description": ""},
    )


def _realises(
    table: str, fk: str, src: str, dst: str, relation: str, cardinality: str = "MANY_TO_ONE"
) -> tuple[Node, Edge]:
    col = Node(id=f"col:table:raw.{table}.{fk}", kind="Column", name=fk, layer="raw")
    return col, Edge(
        src=col.id,
        dst=f"relation:{relation}",
        kind="realises",
        props={"from_concept": src, "to_concept": dst, "fk_column": fk, "fk_table": table, "cardinality": cardinality},
    )


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
    raw_col, realises = _realises(
        "futures_prices", "commodity_id", "PriceObservation", "Commodity", "price_observation_of_commodity"
    )
    _write(
        pdir,
        [
            (
                [_relation("price_observation_of_commodity"), _relation("import_tariff_on_commodity"), raw_col],
                [realises],
            ),
            _mart("dim_commodities", {"commodity_id": KEY}, concept="Commodity"),
            _mart(
                "fct_commodity_prices_daily",
                {"price_id": KEY, "commodity_id": FK, "close_price": {"role": "unit_price"}},
                concept="PriceObservation",
            ),
            # Derived fact, no concept declared, still keyed on a commodity.
            _mart("fct_lot_values", {"lot_id": KEY, "commodity_id": FK}),
            # Fed by a dbt seed: no raw table, so no realises edge exists for it.
            _mart("fct_tariffs", {"tariff_id": KEY, "commodity_id": FK}, concept="ImportTariff"),
            # One row per commodity, but not the entity and not a foreign key.
            _mart("rpt_board", {"commodity_id": KEY}),
        ],
    )
    return build_manifest(pdir, "commodity", "commodity-x")


def _conditions(manifest: dict) -> dict[str, str]:
    return {r["condition"]: r["properties"]["pf.relation"] for r in manifest["relationships"]}


def test_a_plural_entity_is_found_from_its_declared_concept(commodity) -> None:
    rels = _conditions(commodity)
    assert (
        rels["fct_commodity_prices_daily.commodity_id = dim_commodities.commodity_id"]
        == "price_observation_of_commodity"
    )


def test_every_mart_declaring_the_foreign_key_joins(commodity) -> None:
    assert "fct_lot_values.commodity_id = dim_commodities.commodity_id" in _conditions(commodity)


def test_a_declared_mart_binds_without_a_raw_table(commodity) -> None:
    rels = _conditions(commodity)
    assert rels["fct_tariffs.commodity_id = dim_commodities.commodity_id"] == "import_tariff_on_commodity"


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
    raw_col, realises = _realises("charges", "customer_id", "Payment", "Customer", "customer_pays_payment")
    _write(
        pdir,
        [
            ([_relation("customer_pays_payment"), raw_col], [realises]),
            _mart("dim_customers", {"customer_id": KEY}),
            _mart("fct_payments", {"payment_id": KEY, "customer_id": {"role": "foreign_key"}}),
        ],
    )
    manifest = build_manifest(pdir, "acme", "acme-x")
    assert _conditions(manifest) == {"fct_payments.customer_id = dim_customers.customer_id": "customer_pays_payment"}


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
    flag = Node(
        id=mcol("fct_x", "is_ok"),
        kind="Column",
        name="is_ok",
        layer="marts",
        props={"role": "", "pii": False, "model": "fct_x", "data_type": None},
    )
    nodes = [Node(id=mid("fct_x"), kind="Model", name="fct_x", layer="marts"), flag]
    _add_physical_columns(tmp_path, "p", nodes, [])
    assert {n.name: n.props["data_type"] for n in nodes if n.kind == "Column"} == {"is_ok": "BOOLEAN", "n": "INTEGER"}
    assert len(nodes) == 3  # the declared node was typed in place, not duplicated


# ------------------------------------------------------- cubes and views ----


def _metric(name: str, kind: str, **props) -> Node:
    return Node(
        id=f"metric:{name}", kind="Metric", name=name, layer="semantic", label=name, props={"type": kind, **props}
    )


def _dims(names: list[tuple[str, str]]) -> list[Node]:
    return [
        Node(id=f"dim:{i}", kind="Dimension", name=n, layer="semantic", label="", props={"type": t})
        for i, (n, t) in enumerate(names)
    ]


def _exposure(name: str, models: list[str]) -> tuple[list, list]:
    node = Node(
        id=f"exposure:{name}",
        kind="Exposure",
        name=name,
        layer="consumption",
        props={"type": "dashboard", "owner": "Research"},
    )
    return [node], [Edge(src=f"model:{m}", dst=node.id, kind="feeds") for m in models]


def test_a_conformed_dimension_appears_once_in_the_cube(tmp_path: Path) -> None:
    """A dimension is declared per semantic model, so `commodity_id` arrives from
    every fact that has it. A cube is a flat namespace: duplicates make the
    manifest invalid and every planner reading it picks an arbitrary winner."""
    pdir = _project(tmp_path, "commodity", EXTENSION)
    _write(
        pdir,
        [
            _mart("dim_commodities", {"commodity_id": KEY}, concept="Commodity"),
            _mart("fct_commodity_prices_daily", {"price_id": KEY, "commodity_id": FK}, concept="PriceObservation"),
            (
                [
                    Node(
                        id="metric:avg_price",
                        kind="Metric",
                        name="avg_price",
                        layer="semantic",
                        label="Avg Price",
                        props={"type": "ratio"},
                    ),
                    *_dims(
                        [
                            ("commodity_id", "categorical"),
                            ("commodity_id", "categorical"),
                            ("price_basis", "categorical"),
                            ("price_date", "time"),
                            ("price_date", "time"),
                        ]
                    ),
                ],
                [],
            ),
        ],
    )
    cube = build_manifest(pdir, "commodity", "commodity-x")["cubes"][0]
    assert [d["name"] for d in cube["dimensions"]] == ["commodity_id", "price_basis"]
    assert [d["name"] for d in cube["timeDimensions"]] == ["price_date"]


def test_a_view_is_generated_for_every_mart_an_exposure_names(tmp_path: Path) -> None:
    """An exposure is the only place anyone states *this is a surface people
    read*, so views derive from it rather than from an `rpt_` name prefix."""
    pdir = _project(tmp_path, "commodity", EXTENSION)
    _write(
        pdir,
        [
            _mart("dim_commodities", {"commodity_id": KEY}, concept="Commodity"),
            _mart("fct_commodity_prices_daily", {"price_id": KEY, "commodity_id": FK}, concept="PriceObservation"),
            _mart("fct_unread", {"x_id": KEY, "commodity_id": FK}),
            _exposure("price_board", ["fct_commodity_prices_daily"]),
            ([_relation("price_observation_of_commodity")], []),
        ],
    )
    views = build_manifest(pdir, "commodity", "commodity-x")["views"]
    assert [v["name"] for v in views] == ["fct_commodity_prices_daily_view"]
    # The view denormalises along the relationship already derived, and renames
    # the joined key so the surface has no duplicate column. Models are named
    # BARE: a `catalog.schema.model` reference inside a view statement is passed
    # to the warehouse verbatim instead of being resolved to a tableReference,
    # and every query against the view dies on a catalog that does not exist.
    stmt = views[0]["statement"]
    join = (
        "from fct_commodity_prices_daily\n  left join dim_commodities on "
        "fct_commodity_prices_daily.commodity_id = dim_commodities.commodity_id"
    )
    assert join in stmt
    assert "commodity.commodity_x." not in stmt
    assert "dim_commodities.commodity_id as commodities_commodity_id" in stmt


def test_a_mart_read_by_several_exposures_is_one_view(tmp_path: Path) -> None:
    """A hand-written board and the generated page for every metric on the same
    mart are one surface with several readers, not several surfaces. Keyed by
    exposure this collided on the view name."""
    pdir = _project(tmp_path, "commodity", EXTENSION)
    _write(
        pdir,
        [
            _mart("dim_commodities", {"commodity_id": KEY}, concept="Commodity"),
            _mart("fct_commodity_prices_daily", {"price_id": KEY, "commodity_id": FK}, concept="PriceObservation"),
            _exposure("price_board", ["fct_commodity_prices_daily"]),
            _exposure("report_avg_price", ["fct_commodity_prices_daily"]),
        ],
    )
    views = build_manifest(pdir, "commodity", "commodity-x")["views"]
    assert len(views) == 1
    assert views[0]["properties"]["pf.exposures"] == "price_board, report_avg_price"


def test_a_hidden_column_stays_hidden_in_a_view(tmp_path: Path) -> None:
    """A view is a wider surface than a model. Honouring isHidden here is the
    only thing between a PII column and an NL query that selects it back out."""
    pdir = _project(tmp_path, "commodity", EXTENSION)
    _write(
        pdir,
        [
            _mart("dim_commodities", {"commodity_id": KEY}, concept="Commodity"),
            _mart(
                "fct_commodity_prices_daily",
                {"price_id": KEY, "commodity_id": FK, "trader_email": {"role": "email", "pii": True}},
                concept="PriceObservation",
            ),
            _exposure("price_board", ["fct_commodity_prices_daily"]),
        ],
    )
    manifest = build_manifest(pdir, "commodity", "commodity-x")
    fact = next(m for m in manifest["models"] if m["name"] == "fct_commodity_prices_daily")
    assert next(c for c in fact["columns"] if c["name"] == "trader_email")["isHidden"]
    assert "trader_email" not in manifest["views"][0]["statement"]


def test_a_cube_measure_is_real_sql_or_it_is_not_emitted(tmp_path: Path) -> None:
    """The placeholder was the metric name behind `--`, which parses as a comment.

    The whole cube then failed to analyse, and every query against its *base
    object* — the busiest mart in the project — died with "Expected: an
    expression, found: EOF". A missing measure costs one metric; an unparseable
    one costs the mart.
    """
    pdir = _project(tmp_path, "commodity", EXTENSION)
    _write(
        pdir,
        [
            _mart("dim_commodities", {"commodity_id": KEY}, concept="Commodity"),
            _mart("fct_commodity_prices_daily", {"price_id": KEY, "commodity_id": FK}, concept="PriceObservation"),
            (
                [
                    _metric("price_total", "simple", agg="sum", expr="close_price"),
                    _metric("priced_days", "simple", agg="count", expr="close_price"),
                    _metric("avg_price", "ratio", numerator="price_total", denominator="priced_days"),
                    # Window semantics a cube measure cannot express.
                    _metric("price_mom", "derived"),
                    *_dims([("commodity_id", "categorical")]),
                ],
                [],
            ),
        ],
    )
    cube = build_manifest(pdir, "commodity", "commodity-x")["cubes"][0]
    got = {m["name"]: m["expression"] for m in cube["measures"]}
    assert got == {
        "price_total": "sum(close_price)",
        "priced_days": "count(close_price)",
        # A ratio re-divides; it never averages an average.
        "avg_price": "sum(close_price) / nullif(count(close_price), 0)",
    }
    assert not any(m["expression"].lstrip().startswith("--") for m in cube["measures"])


# ------------------------------------------------- the OKF projection --------
#
# `pf.projections.okf` renders the semantic layer as an Open Knowledge Format
# bundle and validates it through the vendored OKF Weaver models before a file
# is written. These pin what makes that a projection rather than a guess: it is
# byte-stable, it carries no machine fact, confidence is a declaration's
# presence and not a model's opinion, hidden columns never travel, every
# concept links up to the platform bundle, and the checker can fail.
from conftest import REPO_ROOT as _REPO


def _okf():
    from pf.projections import okf

    return okf


def _first_modelled() -> tuple[str, str] | None:
    """The first project whose MDL projects a model — the bundle has tables there."""
    import json

    for p in sorted((_REPO / "groups").glob("*/projects/*/mdl/mdl.json")):
        if json.loads(p.read_text(encoding="utf-8")).get("models"):
            return p.parents[3].name, p.parents[1].name
    return None


def _demo(tmp_path: Path, hidden: bool = False) -> Path:
    """A project with a two-column model in its MDL and nothing else."""
    import json

    pdir = tmp_path / "groups" / "demo" / "projects" / "demo-us"
    (pdir / "mdl").mkdir(parents=True)
    cols = [
        {
            "name": "order_id",
            "type": "VARCHAR",
            "notNull": True,
            "isHidden": False,
            "properties": {"pf.role": "natural_key"},
        },
        {"name": "note", "type": "VARCHAR", "notNull": False, "isHidden": hidden, "properties": {}},
    ]
    (pdir / "mdl" / "mdl.json").write_text(
        json.dumps(
            {
                "models": [
                    {
                        "name": "fct_orders",
                        "primaryKey": "order_id",
                        "columns": cols,
                        "properties": {"description": "One row per order.", "layer": "marts", "grain": "order"},
                    }
                ],
                "relationships": [],
            }
        ),
        encoding="utf-8",
    )
    return tmp_path


def test_a_bundle_is_validated_through_the_vendored_models_and_conformant(tmp_path: Path) -> None:
    okf = _okf()
    scope = _first_modelled()
    if scope is None:
        pytest.skip("no project with an MDL model")
    files = okf.build_project(_REPO, *scope)
    tables = [k for k in files if k.startswith("tables/")]
    assert tables and "index.md" in files and "log.md" in files
    assert f"okf_x_tables: {len(tables)}" in files["index.md"]
    for rel, text in files.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(text, encoding="utf-8")
    assert okf.conformance(tmp_path) == []
    models = okf.vendored(_REPO)
    assert models.OKF_SPEC_VERSION == "0.1"


def test_the_bundle_is_byte_stable_and_dated_by_nothing() -> None:
    import re

    okf = _okf()
    scope = _first_modelled()
    if scope is None:
        pytest.skip("no project with an MDL model")
    a, b = okf.build_project(_REPO, *scope), okf.build_project(_REPO, *scope)
    assert a == b
    joined = "\n".join(a.values()) + "\n".join(okf.build_platform(_REPO).values())
    assert not re.search(r"\b20\d\d-\d\d-\d\dT", joined), "the port drops the weaver's timestamp on purpose"
    assert str(_REPO) not in joined


def test_confidence_is_a_declaration_not_a_guess(tmp_path: Path) -> None:
    """1.0 where the platform holds a role or a description, 0.0 where it holds none."""
    okf = _okf()
    files = okf.build_project(_demo(tmp_path), "demo", "demo-us")
    table = files["tables/fct_orders.md"]
    assert "okf_x_table_confidence: 1.0" in table  # the model has a description
    assert "| `note` | VARCHAR |  | — | 0.00 |" in table  # no role, nothing declared
    assert "okf_x_source_of_truth: true" in table  # a mart


def test_hidden_columns_are_withheld_and_counted(tmp_path: Path) -> None:
    okf = _okf()
    table = okf.build_project(_demo(tmp_path, hidden=True), "demo", "demo-us")["tables/fct_orders.md"]
    assert "`note`" not in table
    assert "okf_x_columns_withheld: 1" in table


def test_the_platform_bundle_names_every_class_and_role() -> None:
    from pf.ontology.model import load_ontology

    okf = _okf()
    files = okf.build_platform(_REPO)
    onto = load_ontology()
    assert {k for k in files if k.startswith("concepts/")} == {f"concepts/{c}.md" for c in onto.classes}
    assert {k for k in files if k.startswith("roles/")} == {f"roles/{r}.md" for r in onto.roles}
    assert all("type: Concept" in files[k] for k in files if k.startswith("concepts/"))


def test_a_project_concept_links_up_to_the_platform_bundle() -> None:
    """The connection: a platform-defined concept file points at the platform's file for it."""
    okf = _okf()
    scope = _first_modelled()
    if scope is None:
        pytest.skip("no project with an MDL model")
    files = okf.build_project(_REPO, *scope)
    pdir = _REPO / "groups" / scope[0] / "projects" / scope[1]
    index_link = next(line for line in files["index.md"].splitlines() if line.startswith("okf_x_platform_bundle:"))
    target = (pdir / "okf" / index_link.split(":", 1)[1].strip()).resolve()
    assert target == (_REPO / "platform" / "okf" / "index.md").resolve()
    platform_defined = [k for k in files if k.startswith("concepts/") and "okf_x_defined_in: platform" in files[k]]
    for k in platform_defined:
        link = next(line for line in files[k].splitlines() if line.startswith("okf_x_platform_concept:"))
        assert (pdir / "okf" / "concepts" / link.split(":", 1)[1].strip()).resolve() == (
            _REPO / "platform" / "okf" / k
        ).resolve()


def test_the_checker_fails_on_drift_and_on_a_file_without_a_type(tmp_path: Path) -> None:
    okf = _okf()
    root = _demo(tmp_path)
    assert okf.check_project(root, "demo", "demo-us")[0].endswith("`pf tool okf build demo demo-us`")
    okf.write_project(root, "demo", "demo-us")
    assert okf.check_project(root, "demo", "demo-us") == []
    out = root / "groups" / "demo" / "projects" / "demo-us" / "okf"
    (out / "tables" / "fct_orders.md").write_text("edited\n", encoding="utf-8")
    problems = okf.check_project(root, "demo", "demo-us")
    assert any("stale" in p for p in problems) and any("no YAML frontmatter" in p for p in problems)


def test_the_tool_claims_its_directory_and_is_registered() -> None:
    from pf import architecture as arch
    from pf.tools import all_tools

    assert "okf" in all_tools()
    keys = {f.key for f in arch.features()}
    assert "tool_okf" in keys, "okf/ would be an unmapped directory in every project"
