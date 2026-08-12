"""Build the project knowledge graph from artefacts that already exist.

Inputs (each optional — the builder degrades gracefully):
  contracts/annotations.yaml        ontology annotations exported by dlt sources
  transform/target/manifest.json    dbt models, columns, tests, exposures, lineage
  transform/target/semantic_manifest.json   MetricFlow metrics and dimensions
  the platform ontology             concept nodes and the topology
"""

from __future__ import annotations

import json
from pathlib import Path

from pf.ontology.annotate import load_annotations
from pf.ontology.model import load_ontology
from pf.kg.store import Edge, Graph, Node, open_graph


def cid(name: str) -> str: return f"concept:{name}"
def sid(name: str) -> str: return f"source:{name}"
def tid(source: str, table: str) -> str: return f"table:{source}.{table}"
def tcol(source: str, table: str, col: str) -> str: return f"col:table:{source}.{table}.{col}"
def mid(name: str) -> str: return f"model:{name}"
def mcol(model: str, col: str) -> str: return f"col:model:{model}.{col}"
def metid(name: str) -> str: return f"metric:{name}"
def dimid(name: str) -> str: return f"dim:{name}"
def expid(name: str) -> str: return f"exposure:{name}"


def build_graph(project_dir: str | Path, group: str = "", project: str = "") -> dict[str, int]:
    """(Re)build the graph for one project. Returns node counts by kind."""
    root = Path(project_dir)
    graph_path = root / "kg" / "graph.duckdb"

    nodes: list[Node] = []
    edges: list[Edge] = []

    _add_ontology(nodes, edges)
    _add_annotations(root, nodes, edges)
    _add_dbt(root, nodes, edges)
    _add_semantic(root, nodes, edges)

    nodes.append(Node(
        id=f"project:{project or root.name}", kind="Project", name=project or root.name,
        layer="project", label=f"{group}/{project}".strip("/"),
        props={"group": group, "path": str(root)},
    ))

    known = {n.id for n in nodes}
    edges = [e for e in edges if e.src in known and e.dst in known]

    with open_graph(graph_path) as g:
        g.reset()
        g.add_nodes(nodes)
        g.add_edges(edges)
        counts = g.counts()

    _export_json(graph_path, root / "kg" / "graph.json")
    return counts


# ---------------------------------------------------------------- ontology --
def _add_ontology(nodes: list[Node], edges: list[Edge]) -> None:
    onto = load_ontology()
    for name, cls in onto.classes.items():
        nodes.append(Node(
            id=cid(name), kind="Concept", name=name, layer="ontology",
            label=cls.description,
            props={"abstract": cls.abstract, "parent": cls.parent},
        ))
    for e in onto.edges:
        edges.append(Edge(src=cid(e.src), dst=cid(e.dst), kind="links_to",
                          props={"type": e.type, "cardinality": e.cardinality}))


# ------------------------------------------------------------- annotations --
def _add_annotations(root: Path, nodes: list[Node], edges: list[Edge]) -> None:
    anns = load_annotations(root / "contracts" / "annotations.yaml")
    onto = load_ontology()
    pii = onto.pii_roles()

    for ann in anns:
        source = ann.source or "raw"
        table = ann.resource
        s_id, t_id = sid(source), tid(source, table)

        if not any(n.id == s_id for n in nodes):
            nodes.append(Node(id=s_id, kind="Source", name=source, layer="raw",
                              label=f"dlt source {source}"))

        nodes.append(Node(
            id=t_id, kind="Table", name=table, layer="raw", label=ann.description,
            props={"concept": ann.concept, "grain": ann.grain, "source": source},
        ))
        edges.append(Edge(src=s_id, dst=t_id, kind="contains"))
        edges.append(Edge(src=t_id, dst=cid(ann.concept), kind="instantiates"))

        for col, role in ann.roles.items():
            c_id = tcol(source, table, col)
            nodes.append(Node(
                id=c_id, kind="Column", name=col, layer="raw", label=role,
                props={"role": role, "pii": role in pii, "table": table},
            ))
            edges.append(Edge(src=t_id, dst=c_id, kind="has_column"))

        for col, target in ann.links.items():
            c_id = tcol(source, table, col)
            if not any(n.id == c_id for n in nodes):
                nodes.append(Node(id=c_id, kind="Column", name=col, layer="raw",
                                  label="foreign_key",
                                  props={"role": "foreign_key", "pii": False, "table": table}))
                edges.append(Edge(src=t_id, dst=c_id, kind="has_column"))
            edges.append(Edge(src=c_id, dst=cid(target), kind="links_to"))


# --------------------------------------------------------------------- dbt --
def _add_dbt(root: Path, nodes: list[Node], edges: list[Edge]) -> None:
    manifest_path = root / "transform" / "target" / "manifest.json"
    if not manifest_path.exists():
        return
    manifest = json.loads(manifest_path.read_text())

    by_unique: dict[str, str] = {}

    for uid, node in (manifest.get("nodes") or {}).items():
        rtype = node.get("resource_type")
        if rtype == "model":
            name = node["name"]
            n_id = mid(name)
            by_unique[uid] = n_id
            path_parts = (node.get("path") or "").split("/")
            layer = path_parts[0] if path_parts else "marts"
            nodes.append(Node(
                id=n_id, kind="Model", name=name, layer=layer,
                label=(node.get("description") or "").strip().split("\n")[0],
                props={
                    "schema": node.get("schema"),
                    "materialized": (node.get("config") or {}).get("materialized"),
                    "grain": (node.get("meta") or {}).get("grain", ""),
                    "tags": node.get("tags") or [],
                },
            ))
            for col_name, col in (node.get("columns") or {}).items():
                c_id = mcol(name, col_name)
                meta = col.get("meta") or {}
                nodes.append(Node(
                    id=c_id, kind="Column", name=col_name, layer=layer,
                    label=(col.get("description") or "").strip().split("\n")[0],
                    props={"role": meta.get("role", ""), "pii": bool(meta.get("pii", False)),
                           "model": name, "data_type": col.get("data_type")},
                ))
                edges.append(Edge(src=n_id, dst=c_id, kind="has_column"))

        elif rtype == "test":
            n_id = f"test:{uid}"
            by_unique[uid] = n_id
            nodes.append(Node(
                id=n_id, kind="Test", name=node.get("name", uid), layer="test",
                label=node.get("test_metadata", {}).get("name", ""),
                props={"severity": (node.get("config") or {}).get("severity", "error")},
            ))

    for uid, exp in (manifest.get("exposures") or {}).items():
        name = exp["name"]
        n_id = expid(name)
        by_unique[uid] = n_id
        owner = exp.get("owner") or {}
        nodes.append(Node(
            id=n_id, kind="Exposure", name=name, layer="consumption",
            label=(exp.get("description") or "").strip().split("\n")[0],
            props={"type": exp.get("type"), "owner": owner.get("name"),
                   "email": owner.get("email"), "url": exp.get("url")},
        ))

    # lineage: child depends on parents
    child_map = manifest.get("child_map") or {}
    parent_map = manifest.get("parent_map") or {}
    for child, parents in parent_map.items():
        c_id = by_unique.get(child)
        if not c_id:
            continue
        for parent in parents:
            p_id = by_unique.get(parent)
            if p_id:
                kind = "tested_by" if c_id.startswith("test:") else "derives_from"
                src, dst = (p_id, c_id) if kind == "derives_from" else (p_id, c_id)
                edges.append(Edge(src=src, dst=dst, kind=kind))
            else:
                # source nodes are declared in `sources`, map by table name
                src_node = (manifest.get("sources") or {}).get(parent)
                if src_node:
                    table = src_node.get("name")
                    source = src_node.get("source_name")
                    edges.append(Edge(src=tid(source, table), dst=c_id, kind="derives_from"))
    _ = child_map


# ---------------------------------------------------------------- semantic --
def _add_semantic(root: Path, nodes: list[Node], edges: list[Edge]) -> None:
    sm_path = root / "transform" / "target" / "semantic_manifest.json"
    if not sm_path.exists():
        return
    sm = json.loads(sm_path.read_text())

    measure_owner: dict[str, str] = {}
    for model in sm.get("semantic_models") or []:
        model_ref = (model.get("node_relation") or {}).get("alias") or model.get("name")
        for measure in model.get("measures") or []:
            measure_owner[measure["name"]] = model_ref
        for dim in model.get("dimensions") or []:
            d_id = dimid(f"{model.get('name')}__{dim['name']}")
            nodes.append(Node(
                id=d_id, kind="Dimension", name=dim["name"], layer="semantic",
                label=dim.get("description") or "",
                props={"type": dim.get("type"), "semantic_model": model.get("name")},
            ))
            if model_ref:
                edges.append(Edge(src=mid(model_ref), dst=d_id, kind="grouped_by"))

    for metric in sm.get("metrics") or []:
        name = metric["name"]
        n_id = metid(name)
        nodes.append(Node(
            id=n_id, kind="Metric", name=name, layer="semantic",
            label=metric.get("label") or metric.get("description") or "",
            props={"type": metric.get("type"),
                   "description": metric.get("description") or ""},
        ))
        tp = metric.get("type_params") or {}
        measures = []
        if tp.get("measure"):
            measures.append(tp["measure"].get("name") if isinstance(tp["measure"], dict) else tp["measure"])
        for key in ("numerator", "denominator"):
            v = tp.get(key)
            if isinstance(v, dict) and v.get("name"):
                edges.append(Edge(src=metid(v["name"]), dst=n_id, kind="derives_from"))
        for m in tp.get("metrics") or []:
            ref = m.get("name") if isinstance(m, dict) else m
            if ref and ref != name:
                edges.append(Edge(src=metid(ref), dst=n_id, kind="derives_from"))
        for measure in measures:
            owner = measure_owner.get(measure)
            if owner:
                edges.append(Edge(src=mid(owner), dst=n_id, kind="measures",
                                  props={"measure": measure}))


def _export_json(graph_path: Path, out_path: Path) -> None:
    with open_graph(graph_path, read_only=True) as g:
        payload = {
            "nodes": [
                {"id": n.id, "kind": n.kind, "name": n.name, "layer": n.layer,
                 "label": n.label, "props": n.props}
                for n in g.nodes()
            ],
            "edges": [
                {"src": e.src, "dst": e.dst, "kind": e.kind, "props": e.props}
                for e in g.edges()
            ],
        }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2))
