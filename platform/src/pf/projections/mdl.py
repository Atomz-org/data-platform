"""Project the knowledge graph into a WrenAI MDL manifest.

Field names follow `core/wren-mdl/mdl.schema.json` in Canner/WrenAI, not memory:
  top level   catalog, schema, dataSource, models[], relationships[], cubes[],
              views[], enumDefinitions[], layoutVersion
  model       name, tableReference{catalog,schema,table}, columns[], primaryKey,
              properties{}
  column      name, type, relationship?, isCalculated, notNull, expression?,
              isHidden, properties{}
  relationship name, models[2], joinType, condition
  cube        name, baseObject, measures[], dimensions[], timeDimensions[]

The join `condition` is the payoff of the whole semantic stack. It is not
guessed from a naming convention: the `realises` edge binds a physical foreign
key to a named topology relation, and the identity property on the target class
supplies the other side. Ontology gives meaning, topology gives direction,
annotations give the physical column — the condition falls out.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pf.kg.store import Node, open_graph
from pf.ontology.model import load_ontology

# MDL schema types this as an integer, not a semver string.
LAYOUT_VERSION = 1
JOIN_TYPES = {"ONE_TO_ONE", "ONE_TO_MANY", "MANY_TO_ONE", "MANY_TO_MANY"}


def _identity_column(model: Node, columns: list[Node]) -> str | None:
    """The column a join targets: an explicit key role, else a *_id convention."""
    for c in columns:
        if c.props.get("role") in ("natural_key", "surrogate_key"):
            return c.name
    for c in columns:
        if c.name.endswith("_id"):
            return c.name
    return None


def build_manifest(project_dir: str | Path, group: str, project: str,
                   layer: str = "marts") -> dict[str, Any]:
    """Build an MDL manifest from one project's graph.

    Only `marts` are exposed by default. Staging is an implementation detail; a
    semantic layer that exposes it invites the exact ad-hoc SQL the metrics layer
    exists to prevent.
    """
    onto = load_ontology()
    root = Path(project_dir)
    gp = root / "kg" / "graph.duckdb"

    models: list[dict[str, Any]] = []
    relationships: list[dict[str, Any]] = []
    cubes: list[dict[str, Any]] = []
    enum_definitions: list[dict[str, Any]] = []

    with open_graph(gp, read_only=True) as g:
        wanted = [m for m in g.nodes("Model") if m.layer == layer]
        by_name = {m.name: m for m in wanted}
        cols_of: dict[str, list[Node]] = {}

        for m in wanted:
            cols = [n for n in (g.node(e.dst) for e in g.out_edges(m.id))
                    if n and n.kind == "Column"]
            cols_of[m.name] = cols

            columns: list[dict[str, Any]] = []
            for c in cols:
                role = c.props.get("role") or ""
                columns.append({
                    "name": c.name,
                    "type": _mdl_type(onto, role, c.props.get("data_type")),
                    "isCalculated": False,
                    "notNull": role in ("natural_key", "surrogate_key"),
                    # PII is hidden rather than dropped: the column still exists
                    # for a governed join, but a BI user cannot select it.
                    "isHidden": bool(c.props.get("pii")),
                    "properties": _column_properties(c, role),
                })

            pk = _identity_column(m, cols)
            models.append({
                "name": m.name,
                "tableReference": {"schema": m.props.get("schema") or "main_marts",
                                   "table": m.name},
                "columns": columns,
                **({"primaryKey": pk} if pk else {}),
                "properties": {
                    "description": m.label or "",
                    "grain": m.props.get("grain", ""),
                    "layer": m.layer,
                    "pf.project": project,
                    "pf.group": group,
                },
            })

        # -- relationships, derived from the topology bindings ---------------
        for edge in g.edges():
            if edge.kind != "realises":
                continue
            p = edge.props
            rel_node = g.node(edge.dst)
            if rel_node is None:
                continue

            src_model = _model_for_concept(g, by_name, p["from_concept"], cols_of)
            dst_model = _model_for_concept(g, by_name, p["to_concept"], cols_of)
            if not src_model or not dst_model or src_model == dst_model:
                continue

            fk = _projected_fk(cols_of[src_model], p["fk_column"])
            target_id = _identity_column(by_name[dst_model], cols_of[dst_model])
            if not fk or not target_id:
                continue

            join_type = p.get("cardinality", "MANY_TO_ONE")
            if join_type not in JOIN_TYPES:
                join_type = "MANY_TO_ONE"

            condition = f"{src_model}.{fk} = {dst_model}.{target_id}"
            # Two topology relations can land on the same physical join — e.g.
            # `customer_pays_payment` and `customer_holds_subscription` both
            # reduce to payments.customer_id when there is no subscription mart.
            # MDL requires unique relationship names, and a duplicated condition
            # would double-count in any join planner.
            existing = next((r for r in relationships if r["condition"] == condition), None)
            if existing is not None:
                # Record the alias rather than dropping it: the second relation is
                # real semantics, it just has no distinct physical join here.
                aliases = existing["properties"].setdefault("pf.also_realises", "")
                existing["properties"]["pf.also_realises"] = ", ".join(
                    filter(None, [aliases, rel_node.name]))
                continue

            relationships.append({
                "name": f"{src_model}_{dst_model}",
                "models": [src_model, dst_model],
                "joinType": join_type,
                "condition": condition,
                "properties": {
                    "pf.relation": rel_node.name,
                    "pf.label": rel_node.props.get("label", ""),
                    "pf.inverse": rel_node.props.get("inverse", ""),
                    "pf.description": rel_node.props.get("description", ""),
                },
            })

        # -- cubes, from the semantic layer ----------------------------------
        metrics = g.nodes("Metric")
        dims = g.nodes("Dimension")
        if metrics:
            base = _busiest_model(g, metrics, by_name)
            measures = [{
                "name": mt.name,
                "expression": mt.props.get("expression") or f"-- {mt.name}",
                "type": "DOUBLE",
                "description": mt.label or mt.props.get("description", ""),
                "properties": {"pf.metric_type": mt.props.get("type", "simple")},
            } for mt in metrics]
            cube_dims = [{
                "name": d.name, "expression": d.name, "type": "VARCHAR",
                "description": d.label or "",
            } for d in dims if d.props.get("type") != "time"]
            time_dims = [{
                "name": d.name, "expression": d.name, "type": "TIMESTAMP",
                "description": d.label or "",
            } for d in dims if d.props.get("type") == "time"]
            if base:
                cubes.append({
                    "name": f"{project.replace('-', '_')}_core",
                    "baseObject": base,
                    "measures": measures,
                    "dimensions": cube_dims,
                    "timeDimensions": time_dims,
                })

        # -- enums, from status_enum columns ---------------------------------
        for m in wanted:
            for c in cols_of[m.name]:
                if c.props.get("role") == "status_enum" and c.props.get("values"):
                    enum_definitions.append({
                        "name": f"{m.name}_{c.name}",
                        "values": [{"name": v, "value": v} for v in c.props["values"]],
                    })

    manifest: dict[str, Any] = {
        "catalog": group.replace("-", "_"),
        "schema": project.replace("-", "_"),
        "dataSource": "DUCKDB",
        "layoutVersion": LAYOUT_VERSION,
        "models": models,
        "relationships": relationships,
        "views": [],
        "cubes": cubes,
    }
    if enum_definitions:
        manifest["enumDefinitions"] = enum_definitions
    return manifest


def _mdl_type(onto, role: str, data_type: str | None) -> str:
    if role and role in onto.roles:
        from pf.ontology.model import MDL_TYPES
        return MDL_TYPES.get(onto.roles[role].datatype, "VARCHAR")
    if data_type:
        d = data_type.upper()
        for token in ("VARCHAR", "BIGINT", "INTEGER", "DECIMAL", "DOUBLE",
                      "BOOLEAN", "TIMESTAMP", "DATE"):
            if token in d:
                return token
    return "VARCHAR"


def _column_properties(c: Node, role: str) -> dict[str, Any]:
    props: dict[str, Any] = {}
    if role:
        props["pf.role"] = role
    if c.props.get("pii"):
        # Carried through so a BI layer can enforce masking rather than
        # rediscovering which columns are sensitive.
        props["pf.pii"] = "true"
    if c.label:
        props["description"] = c.label
    return props


def _model_for_concept(g, by_name: dict[str, Node], concept: str,
                       cols_of: dict[str, list[Node]]) -> str | None:
    """Which exposed model instantiates a concept.

    Raw tables carry the `instantiates` edge; marts inherit the concept through
    lineage. Prefer a mart whose name mentions the concept, else the first mart
    downstream of a table that instantiates it.
    """
    lowered = concept.lower()
    for name in by_name:
        if lowered in name.lower():
            return name
    for table in g.nodes("Table"):
        if table.props.get("concept") != concept:
            continue
        seen, stack = set(), [table.id]
        while stack:
            cur = stack.pop()
            for e in g.out_edges(cur):
                if e.kind != "feeds" or e.dst in seen:
                    continue
                seen.add(e.dst)
                n = g.node(e.dst)
                if n and n.kind == "Model" and n.name in by_name:
                    return n.name
                stack.append(e.dst)
    return None


def _projected_fk(columns: list[Node], raw_col: str) -> str | None:
    """The FK's name in the exposed model; staging may have renamed it."""
    names = {c.name for c in columns}
    if raw_col in names:
        return raw_col
    if not raw_col.endswith("_id") and f"{raw_col}_id" in names:
        return f"{raw_col}_id"
    return next((n for n in sorted(names) if n.endswith("_id") and raw_col.split("_")[0] in n), None)


def _busiest_model(g, metrics: list[Node], by_name: dict[str, Node]) -> str | None:
    counts: dict[str, int] = {}
    for mt in metrics:
        for e in g.in_edges(mt.id):
            n = g.node(e.src)
            if n and n.kind == "Model" and n.name in by_name:
                counts[n.name] = counts.get(n.name, 0) + 1
    if counts:
        return max(counts, key=counts.get)
    return next(iter(by_name), None)


def export(project_dir: str | Path, group: str, project: str,
           out: str | Path | None = None) -> Path:
    manifest = build_manifest(project_dir, group, project)
    path = Path(out) if out else Path(project_dir) / "mdl" / "mdl.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return path
