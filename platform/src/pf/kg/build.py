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

from pf.kg.store import Edge, Node, open_graph
from pf.ontology.annotate import load_annotations
from pf.ontology.model import load_group_ontology, load_ontology


def cid(name: str) -> str: return f"concept:{name}"
def sid(name: str) -> str: return f"source:{name}"
def tid(source: str, table: str) -> str: return f"table:{source}.{table}"
def tcol(source: str, table: str, col: str) -> str: return f"col:table:{source}.{table}.{col}"
def mid(name: str) -> str: return f"model:{name}"
def mcol(model: str, col: str) -> str: return f"col:model:{model}.{col}"
def metid(name: str) -> str: return f"metric:{name}"
def dimid(name: str) -> str: return f"dim:{name}"
def expid(name: str) -> str: return f"exposure:{name}"
def relid(name: str) -> str: return f"relation:{name}"
def propid(cls: str, prop: str) -> str: return f"property:{cls}.{prop}"
def polid(pid: str) -> str: return f"policy:{pid}"
def evid(eid: str) -> str: return f"evidence:{eid}"


def _add_physical_columns(root: Path, project: str, nodes: list[Node],
                          edges: list[Edge]) -> None:
    """Add columns that exist in the warehouse but are not documented in dbt.

    The manifest only lists columns someone wrote a description for. That is fine
    for docs and fatal for projection: the join keys are usually the columns
    nobody bothered to document, so an MDL manifest built from documented columns
    alone has models with no foreign keys and therefore no relationships.

    Documentation still wins where it exists — it carries the role and PII flags.
    This only fills in what is missing.
    """
    import duckdb

    db = root / "data" / f"{project.replace('-', '_')}.duckdb"
    if not db.exists():
        return

    models = {n.name: n for n in nodes if n.kind == "Model"}
    if not models:
        return
    known = {(n.props.get("model"), n.name) for n in nodes if n.kind == "Column"}

    try:
        con = duckdb.connect(str(db), read_only=True)
    except duckdb.Error:
        return  # a sister holds the write lock; documented columns still stand
    try:
        rows = con.execute(
            "SELECT table_name, column_name, data_type FROM information_schema.columns "
            "WHERE table_schema NOT IN ('information_schema','pg_catalog')"
        ).fetchall()
    except duckdb.Error:
        return
    finally:
        con.close()

    for table, column, data_type in rows:
        model = models.get(table)
        if model is None or (table, column) in known:
            continue
        if column.startswith("_dlt_"):
            continue
        c_id = mcol(table, column)
        nodes.append(Node(
            id=c_id, kind="Column", name=column, layer=model.layer, label="",
            props={"role": _infer_role(column), "pii": False, "model": table,
                   "data_type": data_type, "documented": False},
        ))
        edges.append(Edge(src=model.id, dst=c_id, kind="has_column"))


def _infer_role(column: str) -> str:
    """A conservative guess for undocumented columns. Only structural roles —
    never PII, which must be declared rather than inferred."""
    if column.endswith("_id"):
        return "foreign_key"
    if column.endswith(("_at", "_date")):
        return "event_time"
    return ""


def build_graph(project_dir: str | Path, group: str = "", project: str = "") -> dict[str, int]:
    """(Re)build the graph for one project. Returns node counts by kind."""
    root = Path(project_dir)
    graph_path = root / "kg" / "graph.duckdb"

    nodes: list[Node] = []
    edges: list[Edge] = []

    # The group ontology, not the platform one: a term a steward approved into
    # groups/<g>/ontology/extension.yaml is not usable by dbt, Wren, BI or an
    # agent until it is in the graph, and building from the platform ontology
    # silently drops every approved extension.
    onto = load_group_ontology(_repo_root(root), group) if group else load_ontology()

    _add_ontology(nodes, edges, onto)
    _add_annotations(root, nodes, edges, onto)
    _add_dbt(root, nodes, edges)
    _add_physical_columns(root, project or root.name, nodes, edges)
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
def _add_ontology(nodes: list[Node], edges: list[Edge],
                  onto=None) -> None:
    """Classes, their datatype properties, the named relations between them, and
    the policy chain. This is the semantic spine every projection reads."""
    onto = onto or load_ontology()

    for name, cls in onto.classes.items():
        nodes.append(Node(
            id=cid(name), kind="Concept", name=name, layer="ontology",
            label=cls.description or cls.label,
            props={"abstract": cls.abstract, "parent": cls.parent,
                   "identity": onto.identity_of(name), "label": cls.label},
        ))
        # Datatype properties are nodes, not attributes: a projection needs to
        # address one (an MDL column, an OWL DatatypeProperty), and impact
        # analysis needs to reach it.
        for pname, prop in cls.properties.items():
            nodes.append(Node(
                id=propid(name, pname), kind="Property", name=pname, layer="ontology",
                label=f"{prop.datatype}{' · ' + prop.role if prop.role else ''}",
                props={"datatype": prop.datatype, "role": prop.role,
                       "required": prop.required, "concept": name,
                       "mdl_type": prop.mdl_type, "xsd_type": prop.xsd_type,
                       "is_identity": pname == cls.identity},
            ))
            edges.append(Edge(src=cid(name), dst=propid(name, pname), kind="has_property"))

    # A relation is a node so it can be named, addressed and bound to a physical
    # column. As a bare edge it could not carry a name, an inverse, or a binding.
    for rel in onto.relations:
        nodes.append(Node(
            id=relid(rel.name), kind="Relation", name=rel.name, layer="topology",
            label=rel.describe(),
            props={"domain": rel.domain, "range": rel.range,
                   "cardinality": rel.cardinality,
                   "inverse_cardinality": rel.inverse_cardinality,
                   "label": rel.label, "inverse": rel.inverse,
                   "description": rel.description,
                   "reverse_label": rel.describe(reverse=True)},
        ))
        edges.append(Edge(src=cid(rel.domain), dst=relid(rel.name), kind="domain_of"))
        edges.append(Edge(src=relid(rel.name), dst=cid(rel.range), kind="range_of"))

    _add_policy(onto, nodes, edges)


def _add_policy(onto, nodes: list[Node], edges: list[Edge]) -> None:
    """OpenTopology's chain: intent -> constraint -> artifact -> evidence.

    Policies are in the graph so "is this rule actually enforced, and what proves
    it ran" is a traversal rather than an archaeology exercise across three files.
    """
    for kind in onto.evidence_kinds:
        nodes.append(Node(
            id=evid(kind["id"]), kind="Evidence", name=kind["id"], layer="governance",
            label=kind.get("produces", ""),
            props={"durable": bool(kind.get("durable", False))},
        ))

    for p in onto.policies:
        nodes.append(Node(
            id=polid(p.id), kind="Policy", name=p.id, layer="governance",
            label=p.intent.split("\n")[0][:160],
            props={"constraint": p.constraint, "severity": p.severity,
                   "applies_to": p.applies_to, "params": p.params,
                   "enforced_by": p.enforced_by, "enforced": p.enforced,
                   "intent": p.intent},
        ))
        for e in p.evidence:
            edges.append(Edge(src=polid(p.id), dst=evid(e), kind="evidenced_by"))

        target = p.applies_to
        if target.get("class") and target["class"] != "*":
            edges.append(Edge(src=polid(p.id), dst=cid(target["class"]), kind="governs"))
        elif target.get("class") == "*":
            for name, cls in onto.classes.items():
                if not cls.abstract:
                    edges.append(Edge(src=polid(p.id), dst=cid(name), kind="governs"))


# ------------------------------------------------------------- annotations --
def _repo_root(project_dir: Path) -> Path:
    for p in [project_dir, *project_dir.parents]:
        if (p / "platform").is_dir() and (p / "groups").is_dir():
            return p
    return project_dir


def _add_annotations(root: Path, nodes: list[Node], edges: list[Edge],
                     onto=None) -> None:
    anns = load_annotations(root / "contracts" / "annotations.yaml")
    onto = onto or load_ontology()
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
                                  props={"role": "foreign_key", "pii": False,
                                         "table": table, "links_to": target}))
                edges.append(Edge(src=t_id, dst=c_id, kind="has_column"))
            edges.append(Edge(src=c_id, dst=cid(target), kind="links_to"))

            # Bind the physical key to the relation it realises. This edge is
            # what turns a warehouse-independent topology into a generatable
            # join: the projection reads the column name from here rather than
            # guessing a convention.
            rel = onto.find_relation(ann.concept, target)
            if rel is not None:
                reverse = onto.is_a(ann.concept, rel.range)
                edges.append(Edge(
                    src=c_id, dst=relid(rel.name), kind="realises",
                    props={"from_concept": ann.concept, "to_concept": target,
                           "fk_column": col, "fk_table": table,
                           # Direction matters: the FK sits on the many side, so
                           # a relation traversed backwards is MANY_TO_ONE.
                           "cardinality": rel.inverse_cardinality if reverse
                                          else rel.cardinality,
                           "reverse": reverse},
                ))


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
                # Both kinds run parent -> child; only the label differs.
                kind = "tested_by" if c_id.startswith("test:") else "feeds"
                edges.append(Edge(src=p_id, dst=c_id, kind=kind))
            else:
                # source nodes are declared in `sources`, map by table name
                src_node = (manifest.get("sources") or {}).get(parent)
                if src_node:
                    table = src_node.get("name")
                    source = src_node.get("source_name")
                    edges.append(Edge(src=tid(source, table), dst=c_id, kind="feeds"))
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
                edges.append(Edge(src=metid(v["name"]), dst=n_id, kind="feeds"))
        for m in tp.get("metrics") or []:
            ref = m.get("name") if isinstance(m, dict) else m
            if ref and ref != name:
                edges.append(Edge(src=metid(ref), dst=n_id, kind="feeds"))
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
