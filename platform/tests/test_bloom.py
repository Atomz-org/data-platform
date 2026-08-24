"""The Bloom export.

The invariants worth pinning are the ones whose failure is *silent*: an id
collision fuses two sister projects into one graph and nothing errors, a dropped
nested property just isn't there, a dangling edge only surfaces when Neo4j
rejects the load hours later.
"""

from __future__ import annotations

import csv
import json

import duckdb
import pytest
from pf.bloom import (
    CAPTION,
    KIND_COLOUR,
    PLANE,
    Corpus,
    collect,
    load_cypher,
    perspective,
    readme,
    templates,
    write,
)
from pf.kg.store import EDGE_KINDS, NODE_KINDS

SCHEMA = """
CREATE TABLE kg_nodes (id TEXT PRIMARY KEY, kind TEXT, name TEXT,
                       layer TEXT, label TEXT, props JSON);
CREATE TABLE kg_edges (src TEXT, dst TEXT, kind TEXT, props JSON);
"""


def _project(root, group, project, nodes, edges):
    d = root / "groups" / group / "projects" / project / "kg"
    d.mkdir(parents=True)
    con = duckdb.connect(str(d / "graph.duckdb"))
    con.execute(SCHEMA)
    for n in nodes:
        con.execute("INSERT INTO kg_nodes VALUES (?,?,?,?,?,?)", n)
    for e in edges:
        con.execute("INSERT INTO kg_edges VALUES (?,?,?,?)", e)
    con.close()


@pytest.fixture
def estate(tmp_path):
    """Two sisters that deliberately share ids, plus one project that doesn't."""
    shared = [
        ("model:orders", "Model", "orders", "marts", "", '{"rows": 10}'),
        ("column:orders.id", "Column", "id", "marts", "", "{}"),
        ("concept:Party", "Concept", "Party", "ontology", "",
         '{"abstract": true, "nested": {"a": 1}}'),
    ]
    edges = [("model:orders", "column:orders.id", "has_column", "{}")]
    _project(tmp_path, "acme", "acme-us", shared, edges)
    _project(tmp_path, "acme", "acme-eu", shared, edges)
    _project(tmp_path, "globex", "globex-core", [
        ("policy:pii", "Policy", "pii", "governance", "", "{}"),
        ("model:sales", "Model", "sales", "marts", "", "{}"),
    ], [("policy:pii", "model:sales", "governs", "{}")])
    return tmp_path


# ------------------------------------------------------------------ collect --

def test_collects_every_project(estate):
    c = collect(estate)
    assert len(c.projects) == 3
    assert len(c.nodes) == 8
    assert len(c.edges) == 3


def test_sister_ids_never_merge(estate):
    """The whole reason ids are qualified.

    `model:orders` in acme-us and acme-eu are different models. A bare id would
    make them one node and silently fuse two sisters' lineage — the failure the
    isolation rule exists to prevent, and one that raises nothing.
    """
    c = collect(estate)
    ids = [n["id"] for n in c.nodes]
    assert len(ids) == len(set(ids)), "qualified ids must be unique"
    orders = sorted(n["id"] for n in c.nodes if n["local_id"] == "model:orders")
    assert orders == ["acme/acme-eu#model:orders", "acme/acme-us#model:orders"]


def test_local_id_survives(estate):
    """A Bloom result has to be traceable back to the project graph."""
    c = collect(estate)
    n = next(x for x in c.nodes if x["id"] == "acme/acme-us#model:orders")
    assert n["local_id"] == "model:orders"
    assert (n["group"], n["project"]) == ("acme", "acme-us")


def test_edges_are_qualified_too(estate):
    c = collect(estate)
    assert all("#" in e["start"] and "#" in e["end"] for e in c.edges)
    assert {e["start"] for e in c.edges} <= {n["id"] for n in c.nodes}


def test_nested_props_are_kept_not_dropped(estate):
    """Neo4j cannot nest, but stringifying loses less than discarding."""
    c = collect(estate)
    n = next(x for x in c.nodes if x["local_id"] == "concept:Party")
    assert json.loads(n["props"])["nested"] == {"a": 1}


def test_dangling_edges_are_reported_and_dropped(tmp_path):
    """Neo4j rejects a dangling relationship and names one row. Name them all."""
    _project(tmp_path, "acme", "acme-us",
             [("model:a", "Model", "a", "marts", "", "{}")],
             [("model:a", "model:ghost", "feeds", "{}")])
    c = collect(tmp_path)
    assert c.edges == []
    assert c.dangling == [("feeds", "acme/acme-us#model:ghost")]


def test_empty_estate_is_not_an_error(tmp_path):
    c = collect(tmp_path)
    assert (c.nodes, c.edges, c.projects) == ([], [], [])


# -------------------------------------------------------------- perspective --

def test_every_node_kind_has_a_plane_and_colour():
    """A kind added to the graph but not here renders grey and uncategorised."""
    assert set(PLANE) == set(NODE_KINDS)
    assert set(KIND_COLOUR) == set(NODE_KINDS)
    assert set(CAPTION) == set(NODE_KINDS)


def test_planes_are_only_the_three():
    assert set(PLANE.values()) == {"physical", "semantic", "governance"}


def test_colours_are_distinct():
    """Two kinds sharing a colour is indistinguishable from a rendering bug."""
    assert len(set(KIND_COLOUR.values())) == len(KIND_COLOUR)


def test_perspective_covers_what_the_corpus_holds(estate):
    c = collect(estate)
    p = perspective(c)
    assert {cat["name"] for cat in p["categories"]} == set(c.kinds)
    assert {r["name"] for r in p["relationshipTypes"]} == set(c.edge_kinds)


def test_perspective_captions_on_name(estate):
    p = perspective(collect(estate))
    for cat in p["categories"]:
        assert cat["caption"] == [{"key": "name"}]
        assert any(x["name"] == "name" and x["isCaption"]
                   for x in cat["properties"])


def test_id_is_excluded_from_display(estate):
    """A qualified id is a join key. Captioning on it shows noise."""
    p = perspective(collect(estate))
    for cat in p["categories"]:
        idp = next(x for x in cat["properties"] if x["name"] == "id")
        assert idp["exclude"] is True


def test_column_is_hidden_by_default(estate):
    """78% of the real graph is Column; any view holding it is unreadable."""
    assert perspective(collect(estate))["hiddenCategories"] == ["Column"]


def test_perspective_is_json_serialisable(estate):
    json.dumps(perspective(collect(estate)))


# ----------------------------------------------------------------- templates --

def test_templates_declare_every_parameter_they_use():
    """A `$param` with no declaration is a search phrase that cannot run."""
    import re
    for t in templates():
        used = set(re.findall(r"\$(\w+)", t["cypher"]))
        declared = {p["name"] for p in t["params"]}
        assert used == declared, f"{t['name']}: {used} vs {declared}"


def test_templates_reference_only_real_kinds():
    """A phrase naming a label or type the graph never emits finds nothing."""
    import re
    labels = set(NODE_KINDS)
    for t in templates():
        for lab in re.findall(r":([A-Z]\w+)", t["cypher"]):
            assert lab in labels, f"{t['name']} references unknown label {lab}"
        for rel in re.findall(r"\[:([a-z_|]+)", t["cypher"]):
            for one in rel.split("|"):
                assert one in EDGE_KINDS, f"{t['name']} unknown edge {one}"


def test_template_ids_are_unique():
    ids = [t["id"] for t in templates()]
    assert len(ids) == len(set(ids))


# -------------------------------------------------------------------- cypher --

def test_loader_sets_a_label_for_every_kind():
    c = load_cypher()
    for kind in NODE_KINDS:
        assert f"SET n:{kind}" in c


def test_loader_is_idempotent_by_construction():
    """Re-running must update, not double the graph."""
    c = load_cypher()
    assert "CREATE CONSTRAINT" in c and "IS UNIQUE" in c
    assert "MERGE (n:KgNode {id: row.`id:ID`})" in c
    assert "CREATE (n" not in c


def test_loader_names_the_csvs_it_is_given():
    c = load_cypher("a.csv", "b.csv")
    assert "file:///a.csv" in c and "file:///b.csv" in c


# --------------------------------------------------------------------- write --

def test_write_produces_the_five_files(estate):
    _, paths = write(estate)
    assert [p.name for p in paths] == [
        "nodes.csv", "edges.csv", "load.cypher",
        "data-platform.bloom-perspective.json", "README.md"]
    assert all(p.exists() for p in paths)


def test_csv_round_trips(estate):
    c, paths = write(estate)
    rows = list(csv.DictReader(paths[0].open()))
    assert len(rows) == len(c.nodes)
    assert {r["id:ID"] for r in rows} == {n["id"] for n in c.nodes}


def test_every_written_edge_endpoint_resolves(estate):
    """The check Neo4j would otherwise make for us, hours later."""
    _, paths = write(estate)
    ids = {r["id:ID"] for r in csv.DictReader(paths[0].open())}
    for e in csv.DictReader(paths[1].open()):
        assert e["start:START_ID"] in ids
        assert e["end:END_ID"] in ids


def test_readme_reports_the_real_numbers(estate):
    c = collect(estate)
    text = readme(c)
    assert f"**{len(c.nodes):,} nodes and {len(c.edges):,} relationships**" in text
    for group, project, _, _ in c.projects:
        assert f"`{group}/{project}`" in text


def test_readme_warns_about_dropped_edges(tmp_path):
    _project(tmp_path, "acme", "acme-us",
             [("model:a", "Model", "a", "marts", "", "{}")],
             [("model:a", "model:ghost", "feeds", "{}")])
    assert "dropped for a missing endpoint" in readme(collect(tmp_path))


def test_write_is_repeatable(estate):
    """Two runs over an unchanged graph must produce identical bytes."""
    _, first = write(estate)
    before = [p.read_bytes() for p in first]
    _, second = write(estate)
    assert [p.read_bytes() for p in second] == before


def test_corpus_counts_are_sorted_descending():
    c = Corpus(nodes=[{"kind": "Column"}] * 3 + [{"kind": "Model"}])
    assert list(c.kinds) == ["Column", "Model"]
