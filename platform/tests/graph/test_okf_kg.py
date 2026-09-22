"""The OKF bundle and the knowledge graph, as one surface.

The bundle is what an agent reads to learn what a table means; the graph is
what it queries to learn what touches that table. Kept apart they are two
exports of the same facts that drift the moment one is rebuilt without the
other — and nothing says so, because each one is internally consistent.

These pin the join in both directions: a page names the graph node it
documents and states what only the graph holds (lineage, the readers
downstream, the policies on its concept, the decisions taken about it); the
graph answers back where a node is documented and which pages a change stales.
And `reconcile` is that join as a gate — a page pointing at a node the graph
does not hold is the drift, caught without rebuilding either artefact.

Everything reads tracked artefacts only (`mdl/mdl.json`, `kg/graph.json`,
`okf/**`). A test that needed `kg/graph.duckdb` — gitignored — would pass on a
laptop and skip on every CI runner, which is the same as not existing.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from conftest import REPO_ROOT
from pf.projections import okf

ROOT = REPO_ROOT


def _projects() -> list[tuple[str, str]]:
    groups = ROOT / "groups"
    if not groups.exists():
        return []
    return sorted(
        (g.name, p.name)
        for g in groups.iterdir()
        if g.is_dir() and (g / "projects").is_dir()
        for p in (g / "projects").iterdir()
        if p.is_dir() and not p.name.startswith(".")
    )


# ------------------------------------------------------------- fixtures ----
def _mdl(pdir: Path) -> None:
    """Two models in the MDL — one mart the graph knows, one it does not."""
    (pdir / "mdl").mkdir(parents=True, exist_ok=True)
    (pdir / "mdl" / "mdl.json").write_text(
        json.dumps(
            {
                "models": [
                    {
                        "name": "fct_orders",
                        "primaryKey": "order_id",
                        "columns": [
                            {
                                "name": "order_id",
                                "type": "VARCHAR",
                                "notNull": True,
                                "properties": {"pf.role": "natural_key"},
                            },
                        ],
                        "properties": {"description": "One row per order.", "layer": "marts", "grain": "order"},
                    },
                    {
                        "name": "dim_customers",
                        "primaryKey": "customer_id",
                        "columns": [
                            {"name": "customer_id", "type": "VARCHAR", "notNull": True, "properties": {}},
                        ],
                        "properties": {"description": "One row per customer.", "layer": "marts", "grain": "customer"},
                    },
                ],
                "relationships": [],
            }
        ),
        encoding="utf-8",
    )


def _graph(pdir: Path, nodes: list[dict], edges: list[dict]) -> None:
    (pdir / "kg").mkdir(parents=True, exist_ok=True)
    (pdir / "kg" / "graph.json").write_text(json.dumps({"nodes": nodes, "edges": edges}), encoding="utf-8")


def _node(node_id: str, kind: str, name: str, label: str = "", **props: object) -> dict:
    return {"id": node_id, "kind": kind, "name": name, "layer": "", "label": label, "props": props}


def _edge(src: str, dst: str, kind: str) -> dict:
    return {"src": src, "dst": dst, "kind": kind, "props": {}}


def _demo(tmp_path: Path, with_graph: bool = True) -> Path:
    """A project whose MDL and graph were built from the same state."""
    pdir = tmp_path / "groups" / "demo" / "projects" / "demo-us"
    pdir.mkdir(parents=True)
    _mdl(pdir)
    if not with_graph:
        return tmp_path
    _graph(
        pdir,
        [
            _node("model:fct_orders", "Model", "fct_orders", "One row per order."),
            _node("model:dim_customers", "Model", "dim_customers", "One row per customer."),
            _node("model:stg_orders", "Model", "stg_orders", "Staged orders."),
            _node("col:model:fct_orders.order_id", "Column", "order_id", model="fct_orders"),
            _node("metric:order_count", "Metric", "order_count"),
            _node("metric:orders_mom_change", "Metric", "orders_mom_change"),
            _node("concept:Order", "Concept", "Order", "A purchase."),
            _node("policy:entity-requires-identity", "Policy", "entity-requires-identity",
                  "A class with no identity cannot be joined.", severity="error"),
            _node("decision:ADR-0007", "Decision", "ADR-0007", "Orders are counted at the line, not the header.",
                  status="accepted"),
            _node("exposure:order_board", "Exposure", "order_board", "The order board.",
                  owner="Revenue Team", email="revenue@demo.example"),
        ],
        [
            _edge("model:stg_orders", "model:fct_orders", "feeds"),
            _edge("model:fct_orders", "model:dim_customers", "feeds"),
            _edge("model:fct_orders", "exposure:order_board", "feeds"),
            _edge("model:fct_orders", "metric:order_count", "measures"),
            _edge("model:fct_orders", "metric:orders_mom_change", "measures"),
            _edge("metric:order_count", "metric:orders_mom_change", "feeds"),
            _edge("model:fct_orders", "col:model:fct_orders.order_id", "has_column"),
            _edge("policy:entity-requires-identity", "concept:Order", "governs"),
            _edge("decision:ADR-0007", "model:fct_orders", "decides"),
        ],
    )
    return tmp_path


def _front(text: str) -> dict:
    return yaml.safe_load(text.split("---", 2)[1])


# --------------------------------------------- a page names its own node ----
def test_every_page_names_the_graph_node_it_documents(tmp_path: Path) -> None:
    files = okf.build_project(_demo(tmp_path), "demo", "demo-us")

    assert _front(files["tables/fct_orders.md"])["okf_x_kg_node"] == "model:fct_orders"
    assert _front(files["tables/dim_customers.md"])["okf_x_kg_node"] == "model:dim_customers"


def test_a_node_the_graph_does_not_hold_is_never_claimed(tmp_path: Path) -> None:
    """The key means "this resolves". Written unconditionally it would be a
    pointer nobody could follow, and `reconcile` could not tell drift from a
    convention that never resolved in the first place."""
    root = _demo(tmp_path)
    pdir = root / "groups" / "demo" / "projects" / "demo-us"
    graph = json.loads((pdir / "kg" / "graph.json").read_text())
    graph["nodes"] = [n for n in graph["nodes"] if n["id"] != "model:dim_customers"]
    (pdir / "kg" / "graph.json").write_text(json.dumps(graph), encoding="utf-8")

    files = okf.build_project(root, "demo", "demo-us")
    assert _front(files["tables/dim_customers.md"])["okf_x_kg_node"] is None
    assert "# Lineage" not in files["tables/dim_customers.md"]


def test_without_a_graph_the_bundle_still_builds_and_claims_nothing(tmp_path: Path) -> None:
    files = okf.build_project(_demo(tmp_path, with_graph=False), "demo", "demo-us")

    assert "tables/fct_orders.md" in files
    assert _front(files["tables/fct_orders.md"])["okf_x_kg_node"] is None
    assert _front(files["index.md"])["okf_x_kg_graph"] is None
    assert "# Lineage" not in files["tables/fct_orders.md"]
    assert "# Governance" not in files["tables/fct_orders.md"]


# ------------------------------------------------- what only the graph has --
def test_lineage_is_read_from_the_graph(tmp_path: Path) -> None:
    page = okf.build_project(_demo(tmp_path), "demo", "demo-us")["tables/fct_orders.md"]
    lineage = page.split("# Lineage", 1)[1]

    assert "**Upstream:** `stg_orders`" in lineage
    assert "**Downstream:** [dim_customers](/tables/dim_customers.md)" in lineage
    assert "`order_board` (Revenue Team)" in lineage


def test_a_model_below_the_documented_layer_is_named_but_not_linked(tmp_path: Path) -> None:
    """The graph reaches every staging model; the bundle documents the layer the
    semantic layer projects to BI. A link to a page that was never written reads
    as a missing file rather than as a deliberate boundary."""
    page = okf.build_project(_demo(tmp_path), "demo", "demo-us")["tables/fct_orders.md"]

    assert "`stg_orders`" in page
    assert "(/tables/stg_orders.md)" not in page


def test_every_metric_on_a_table_is_linked_from_its_page(tmp_path: Path) -> None:
    """There was a second row here — "also measured by" — for metrics the graph
    held and the metric collector dropped. The bundle takes its metrics from the
    graph now, so the two lists cannot disagree and the row cannot fire."""
    page = okf.build_project(_demo(tmp_path), "demo", "demo-us")["tables/fct_orders.md"]

    assert "**Also measured by:**" not in page
    for metric in ("order_count", "orders_mom_change"):
        assert f"[{metric}](/metrics/{metric}.md)" in page


def test_a_metric_page_carries_the_metric_graph_around_it(tmp_path: Path) -> None:
    """A derived metric hangs off the metric it is built from, never off a model,
    so no table page can reach it. Said on the metric page or nowhere — and
    changing a definition changes every metric below it."""
    from types import SimpleNamespace

    gf = okf.load_graph(_demo(tmp_path) / "groups" / "demo" / "projects" / "demo-us")
    assert gf is not None
    metric = SimpleNamespace(
        name="order_count", label="Orders", description="How many orders.", kind="simple",
        model="fct_orders", time_column="ordered_at", expression="count(*)", numerator="",
        denominator="", dimensions=[], filter_sql="",
    )

    page = okf._metric_file(metric, gf, {"order_count"})
    assert "okf_x_kg_node: metric:order_count" in page
    assert "**Derived from it:** `orders_mom_change`" in page  # in the graph, no page here


def test_a_reader_is_named_without_its_owners_address(tmp_path: Path) -> None:
    """The bundle is meant to travel. An email in a portable context file is the
    same mistake as a masked column's name in one."""
    files = okf.build_project(_demo(tmp_path), "demo", "demo-us")

    assert "revenue@demo.example" not in "\n".join(files.values())
    assert "Revenue Team" in files["tables/fct_orders.md"]


def test_a_decision_reaches_the_page_it_was_taken_about(tmp_path: Path) -> None:
    page = okf.build_project(_demo(tmp_path), "demo", "demo-us")["tables/fct_orders.md"]
    governance = page.split("# Governance", 1)[1]

    assert "**Decision** ADR-0007" in governance
    assert "Orders are counted at the line, not the header." in governance
    assert "(accepted)" in governance


def test_a_policy_governs_through_the_concept_it_constrains(tmp_path: Path) -> None:
    """A policy is bound to a class, not to a table. The page a reader opens is
    the table's, so the constraint has to travel down the `instantiates` edge or
    it is three files away from where it applies."""
    gf = okf.load_graph(_demo(tmp_path) / "groups" / "demo" / "projects" / "demo-us")
    assert gf is not None

    governed = okf._governance(gf, ["model:fct_orders"], "Order")
    assert any("**Policy** `entity-requires-identity` (error)" in line for line in governed)
    assert okf._governance(gf, ["model:fct_orders"], "") != governed


def test_the_index_states_what_the_graph_reaches_and_what_the_bundle_documents(tmp_path: Path) -> None:
    index = okf.build_project(_demo(tmp_path), "demo", "demo-us")["index.md"]
    front = _front(index)

    assert front["okf_x_kg_graph"] == okf.KG_LINK
    assert front["okf_x_kg_models"] == 3  # the graph's three models
    assert front["okf_x_tables"] == 2  # the two the MDL projects
    assert "Joined to this project's knowledge graph" in index


# ------------------------------------------------------------ the join ------
def test_reconcile_is_clean_when_both_were_built_together(tmp_path: Path) -> None:
    root = _demo(tmp_path)
    okf.write_project(root, "demo", "demo-us")

    join = okf.reconcile(root, "demo", "demo-us")
    assert join.exercised and join.problems == []
    # Six pages: two tables, the two concepts their keys identify, and the two
    # metrics the graph holds. Five resolve; `concept:Customer` is not in this
    # graph, so its page names no node — reported as exactly that rather than
    # counted as either outcome.
    assert (join.pages, join.resolved) == (6, 5)
    assert join.undocumented == ["stg_orders"]
    assert "5/5 page(s) resolve in the graph · 1 name no node" in join.render()
    assert "1 graph model(s) below the documented layer" in join.render()
    assert join.render().startswith("✓")


def test_reconcile_catches_a_graph_rebuilt_without_its_bundle(tmp_path: Path) -> None:
    """The failure this exists for: a model is renamed, `pf kg build` runs, the
    bundle is not rebuilt, and every agent following a page reads about a model
    the warehouse no longer has."""
    root = _demo(tmp_path)
    okf.write_project(root, "demo", "demo-us")
    pdir = root / "groups" / "demo" / "projects" / "demo-us"
    graph = json.loads((pdir / "kg" / "graph.json").read_text())
    for node in graph["nodes"]:
        if node["id"] == "model:dim_customers":
            node["id"], node["name"] = "model:dim_customer", "dim_customer"
    (pdir / "kg" / "graph.json").write_text(json.dumps(graph), encoding="utf-8")

    join = okf.reconcile(root, "demo", "demo-us")
    assert join.dangling == ["tables/dim_customers.md -> model:dim_customers"]
    assert join.problems and "kg/graph.json does not hold" in join.problems[0]
    assert join.render().startswith("⛔")
    assert "run `pf kg build` then `pf tool okf build`" in join.render()


def test_the_gate_fails_on_a_bundle_out_of_step_with_its_graph(tmp_path: Path) -> None:
    root = _demo(tmp_path)
    okf.write_project(root, "demo", "demo-us")
    assert okf.check_project(root, "demo", "demo-us") == []

    pdir = root / "groups" / "demo" / "projects" / "demo-us"
    graph = json.loads((pdir / "kg" / "graph.json").read_text())
    graph["nodes"] = [n for n in graph["nodes"] if n["id"] != "concept:Order"]
    (pdir / "kg" / "graph.json").write_text(json.dumps(graph), encoding="utf-8")

    problems = okf.check_project(root, "demo", "demo-us")
    assert any("concepts/Order.md" in p and "does not hold" in p for p in problems)


def test_what_cannot_be_judged_says_so(tmp_path: Path) -> None:
    """Neither "joined" nor "broken": a project with no graph, or no bundle, is a
    third answer. Reporting it as clean is the green tick for "found nothing"."""
    root = _demo(tmp_path, with_graph=False)
    no_bundle = okf.reconcile(root, "demo", "demo-us")
    assert not no_bundle.exercised and "no okf/" in no_bundle.reason
    assert no_bundle.render().startswith("?")

    okf.write_project(root, "demo", "demo-us")
    no_graph = okf.reconcile(root, "demo", "demo-us")
    assert not no_graph.exercised and "graph has never been built" in no_graph.reason
    assert no_graph.problems == []


def test_the_page_convention_is_defined_once() -> None:
    assert okf.page_rel("Model", "fct_orders") == "okf/tables/fct_orders.md"
    assert okf.page_rel("Concept", "Order") == "okf/concepts/Order.md"
    assert okf.page_rel("Metric", "order_count") == "okf/metrics/order_count.md"
    assert okf.page_rel("Column", "order_id") == ""  # a column is documented on its table's page
    assert okf.page_rel("Model", "") == ""


# --------------------------------------------- the graph answers back -------
def _duckdb_graph(pdir: Path) -> Path:
    """The same graph as `_demo`, in the store the queries read."""
    from pf.kg.store import Edge, Node, open_graph

    payload = json.loads((pdir / "kg" / "graph.json").read_text())
    path = pdir / "kg" / "graph.duckdb"
    with open_graph(path) as g:
        g.add_nodes([Node(id=n["id"], kind=n["kind"], name=n["name"], layer=n["layer"],
                          label=n["label"], props=n["props"]) for n in payload["nodes"]])
        g.add_edges([Edge(src=e["src"], dst=e["dst"], kind=e["kind"]) for e in payload["edges"]])
    return path


def test_a_blast_radius_names_the_bundle_pages_it_stales(tmp_path: Path) -> None:
    from pf.kg.impact import impact_of

    root = _demo(tmp_path)
    okf.write_project(root, "demo", "demo-us")
    pdir = root / "groups" / "demo" / "projects" / "demo-us"

    report = impact_of(_duckdb_graph(pdir), "model:fct_orders")
    assert "okf/tables/fct_orders.md" in report.documents
    assert "okf/tables/dim_customers.md" in report.documents
    assert "okf/tables/stg_orders.md" not in report.documents  # no page, so nothing to stale
    assert "Knowledge bundle pages this stales" in report.render()
    assert report.to_dict()["documents"] == report.documents


def test_a_stale_page_is_never_a_severity(tmp_path: Path) -> None:
    """Regenerating a context file is a chore; breaking a metric is a risk. If
    the bundle moved the needle, every change would read as breaking and the
    gate would be switched off."""
    from pf.kg.impact import impact_of

    root = _demo(tmp_path)
    okf.write_project(root, "demo", "demo-us")
    pdir = root / "groups" / "demo" / "projects" / "demo-us"
    graph_path = _duckdb_graph(pdir)

    before = impact_of(graph_path, "model:dim_customers")
    assert before.documents == ["okf/tables/dim_customers.md"]
    assert before.severity == "safe"  # nothing downstream of it


def test_the_graph_says_where_a_node_is_documented(tmp_path: Path) -> None:
    from pf.kg.query import kg_neighbors

    root = _demo(tmp_path)
    pdir = root / "groups" / "demo" / "projects" / "demo-us"
    graph_path = _duckdb_graph(pdir)
    assert "documented in" not in kg_neighbors(graph_path, "model:fct_orders")

    okf.write_project(root, "demo", "demo-us")
    assert "documented in okf/tables/fct_orders.md" in kg_neighbors(graph_path, "model:fct_orders")


# ------------------------------------------- nothing but tracked artefacts ---
def test_a_bundle_builds_the_same_in_a_checkout_that_has_never_run_dbt(tmp_path: Path) -> None:
    """The failure this guards: the metric pages came from
    `transform/target/semantic_manifest.json`, which is gitignored. The bundle
    was green on a machine that had built the project and told every CI runner
    that fifteen committed metric pages were "no longer in the semantic layer".

    So the test is not "metrics come from the graph" — it is that the projection
    reads nothing git does not carry. Build it from a tree holding the tracked
    inputs alone and the bytes have to match.
    """
    import shutil

    root = _demo(tmp_path)
    pdir = root / "groups" / "demo" / "projects" / "demo-us"
    # what a build leaves behind, and a clone never has
    (pdir / "transform" / "target").mkdir(parents=True)
    (pdir / "transform" / "target" / "semantic_manifest.json").write_text(
        json.dumps({"metrics": [{"name": "ghost", "type": "simple"}], "semantic_models": []}), encoding="utf-8"
    )
    with_target = okf.build_project(root, "demo", "demo-us")

    bare = tmp_path / "bare"
    for rel in ("mdl/mdl.json", "kg/graph.json"):
        dst = bare / "groups" / "demo" / "projects" / "demo-us" / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(pdir / rel, dst)
    without_target = okf.build_project(bare, "demo", "demo-us")

    assert with_target == without_target
    assert not any("ghost" in k for k in with_target), "a gitignored file reached the bundle"


def test_every_metric_the_graph_holds_is_documented(tmp_path: Path) -> None:
    """The collector drops a metric whose measure it cannot turn into SQL, which
    is right for a dashboard that has to run the query and wrong for a bundle
    that has to describe it."""
    specs = okf.metric_specs(okf.load_graph(_demo(tmp_path) / "groups" / "demo" / "projects" / "demo-us"))

    assert sorted(s.name for s in specs) == ["order_count", "orders_mom_change"]
    assert [s.model for s in specs if s.name == "order_count"] == ["fct_orders"]


def test_a_metric_built_on_another_metric_inherits_its_model(tmp_path: Path) -> None:
    """A ratio hangs off other metrics and has no `measures` edge of its own;
    asking the graph directly says "no model" about a metric plainly built on
    one, and the page then documents a measure with nothing under it."""
    specs = {s.name: s for s in okf.metric_specs(okf.load_graph(
        _demo(tmp_path) / "groups" / "demo" / "projects" / "demo-us"))}

    assert specs["orders_mom_change"].model == "fct_orders"


@pytest.mark.parametrize(("group", "project"), _projects(), ids=lambda x: x if isinstance(x, str) else "")
def test_no_committed_bundle_depends_on_an_untracked_file(group: str, project: str) -> None:
    """The same guarantee, against the real bundles: rebuild each one from the
    tracked inputs alone and compare with what is committed."""
    import shutil
    import tempfile

    pdir = ROOT / "groups" / group / "projects" / project
    if not (pdir / okf.OKF_REL / "index.md").is_file():
        pytest.skip("no bundle")
    bare = Path(tempfile.mkdtemp()) / "bare"
    for rel in ("mdl/mdl.json", okf.KG_REL.as_posix()):
        src = pdir / rel
        if src.is_file():
            dst = bare / "groups" / group / "projects" / project / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, dst)
    if (ROOT / "groups" / group / "ontology").is_dir():
        shutil.copytree(ROOT / "groups" / group / "ontology", bare / "groups" / group / "ontology")

    for rel, text in okf.build_project(bare, group, project).items():
        committed = pdir / okf.OKF_REL / rel
        assert committed.is_file(), f"{group}/{project}: {rel} is projected and not committed"
        assert committed.read_text(encoding="utf-8") == text, f"{group}/{project}: {rel} differs in a bare checkout"


# ----------------------------------------------- every project, as committed --
@pytest.mark.parametrize(("group", "project"), _projects(), ids=lambda x: x if isinstance(x, str) else "")
def test_every_committed_bundle_resolves_in_its_committed_graph(group: str, project: str) -> None:
    join = okf.reconcile(ROOT, group, project)
    if not join.exercised:
        pytest.skip(join.reason)
    assert join.problems == []


@pytest.mark.parametrize(("group", "project"), _projects(), ids=lambda x: x if isinstance(x, str) else "")
def test_every_page_of_every_bundle_carries_a_resolvable_node(group: str, project: str) -> None:
    """Not the same check: `reconcile` verifies the ids that are there. This
    verifies there are ids — a bundle built before the graph existed resolves
    perfectly and says nothing."""
    pdir = ROOT / "groups" / group / "projects" / project
    bundle = pdir / okf.OKF_REL
    if not (bundle / "index.md").is_file() or not (pdir / okf.KG_REL).is_file():
        pytest.skip("no bundle or no graph")
    gf = okf.load_graph(pdir)
    assert gf is not None

    for page in sorted(bundle.rglob("*.md")):
        rel = page.relative_to(bundle).as_posix()
        if rel in okf.RESERVED or rel.startswith("weave"):
            continue
        node = okf.frontmatter(page).get(okf.KG_NODE_KEY)
        subject = rel.split("/", 1)[0].rstrip("s").capitalize()
        expected = {"Table": "Model", "Concept": "Concept", "Metric": "Metric"}.get(subject)
        if expected is None:
            continue
        assert node, f"{group}/{project}: {rel} names no graph node"
        assert gf.has(str(node)), f"{group}/{project}: {rel} names {node}, which the graph does not hold"


@pytest.mark.parametrize(("group", "project"), _projects(), ids=lambda x: x if isinstance(x, str) else "")
def test_the_reporting_layer_reaches_the_bundle_of_the_project_it_reads(group: str, project: str) -> None:
    """The Evidence pages under `reporting/` are dbt exposures on the marts they
    query, so the graph holds them — and a table page that does not name its
    readers sends someone renaming a column to read the dbt project to find out
    who breaks."""
    pdir = ROOT / "groups" / group / "projects" / project
    gf = okf.load_graph(pdir)
    tables = pdir / okf.OKF_REL / "tables"
    if gf is None or not tables.is_dir():
        pytest.skip("no graph or no documented table")

    documented = {p.stem for p in tables.glob("*.md")}
    expected = {
        model: [str(e.get("name")) for e in gf.downstream(f"model:{model}", "Exposure")]
        for model in sorted(documented)
    }
    with_readers = {m: names for m, names in expected.items() if names}
    if not with_readers:
        pytest.skip("no exposure reads a documented table")

    for model, names in with_readers.items():
        page = (tables / f"{model}.md").read_text(encoding="utf-8")
        assert "**Read by:**" in page, f"{group}/{project}: {model} is read by {names} and says so nowhere"
        assert names[0] in page  # sorted, so the first is always named — the rest may be summarised


@pytest.mark.parametrize(("group", "project"), _projects(), ids=lambda x: x if isinstance(x, str) else "")
def test_no_bundle_carries_an_address(group: str, project: str) -> None:
    bundle = ROOT / "groups" / group / "projects" / project / okf.OKF_REL
    if not bundle.is_dir():
        pytest.skip("no bundle")
    for page in sorted(bundle.rglob("*.md")):
        assert "@" not in page.read_text(encoding="utf-8").replace("@dbt", ""), f"{page} carries an address"
