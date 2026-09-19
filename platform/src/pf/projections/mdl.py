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

Which *mart* plays each side is read from what the project declared — a model's
`meta.concept` and a column's `meta.links_to` — before any naming heuristic.
The heuristic alone matched `commodity` against `fct_commodity_prices_daily`
rather than `dim_commodities`, joined the fact to itself, and dropped the
relationship without a word.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pf.kg.store import Node, open_graph
from pf.ontology.model import load_group_ontology, load_ontology

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
    root = Path(project_dir)
    onto = _ontology(root, group)
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
        def add(src_model: str, fk: str | None, dst_model: str, target_id: str,
                cardinality: str, rel_node: Node) -> None:
            if not fk or src_model == dst_model:
                return
            join_type = cardinality if cardinality in JOIN_TYPES else "MANY_TO_ONE"
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
                if rel_node.name != existing["properties"]["pf.relation"]:
                    aliases = existing["properties"].setdefault("pf.also_realises", "")
                    existing["properties"]["pf.also_realises"] = ", ".join(
                        filter(None, [aliases, rel_node.name]))
                return
            name = f"{src_model}_{dst_model}"
            if any(r["name"] == name for r in relationships):
                name = f"{name}__{fk}"
            relationships.append({
                "name": name,
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

        for edge in g.edges():
            if edge.kind != "realises":
                continue
            p = edge.props
            rel_node = g.node(edge.dst)
            if rel_node is None:
                continue

            dst_model = _entity_model(onto, g, by_name, p["to_concept"], cols_of)
            if not dst_model:
                continue
            target_id = _target_key(onto, p["to_concept"], cols_of[dst_model])
            if not target_id:
                continue

            sources = _declared_fk_sources(by_name, cols_of, p["from_concept"],
                                           p["to_concept"])
            if not sources:
                src_model = _model_for_concept(g, by_name, p["from_concept"], cols_of)
                if src_model:
                    sources = [(src_model, _projected_fk(cols_of[src_model], p["fk_column"]))]
            for src_model, fk in sources:
                add(src_model, fk, dst_model, target_id,
                    p.get("cardinality", "MANY_TO_ONE"), rel_node)

        # A mart that declares its concept and a foreign key is bound as
        # explicitly as a raw table, so it needs no raw-table edge to reach the
        # topology — a dbt seed feeding it has no annotation to carry one.
        for src_model, m in by_name.items():
            src_concept = m.props.get("concept")
            if not src_concept:
                continue
            for c in cols_of[src_model]:
                target = c.props.get("links_to")
                rel = onto.find_relation(src_concept, target) if target else None
                if rel is None:
                    continue
                dst_model = _entity_model(onto, g, by_name, target, cols_of)
                target_id = _target_key(onto, target, cols_of[dst_model]) if dst_model else None
                rel_node = g.node(f"relation:{rel.name}")
                if not dst_model or not target_id or rel_node is None:
                    continue
                reverse = onto.is_a(src_concept, rel.range)
                add(src_model, c.name, dst_model, target_id,
                    rel.inverse_cardinality if reverse else rel.cardinality, rel_node)

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


def _ontology(root: Path, group: str):
    """The group's vocabulary, not only the platform's.

    The platform ontology alone knows nothing of a group's own roles and
    relations, so a column carrying one fell back to its physical type — or to
    VARCHAR when the manifest had none.
    """
    for p in [root, *root.parents]:
        if (p / "platform").is_dir() and (p / "groups").is_dir():
            try:
                return load_group_ontology(p, group)
            except (OSError, ValueError):
                break
    return load_ontology()


def _entity_model(onto, g, by_name: dict[str, Node], concept: str,
                  cols_of: dict[str, list[Node]]) -> str | None:
    """The mart that *is* a concept — the target side of a join.

    A mart that declares the concept and keys on the class's identity is the
    entity. Anything else falls back to the naming heuristic, preferring a
    dimension, which is what every project that declares nothing relied on.
    """
    identity = onto.identity_of(concept) if onto.has_class(concept) else None
    for name, m in by_name.items():
        if m.props.get("concept") != concept or not identity:
            continue
        keys = {c.name for c in cols_of[name]
                if c.props.get("role") in ("natural_key", "surrogate_key")}
        if identity in keys:
            return name
    return _model_for_concept(g, by_name, concept, cols_of, prefer_dimension=True)


def _target_key(onto, concept: str, columns: list[Node]) -> str | None:
    identity = onto.identity_of(concept) if onto.has_class(concept) else None
    if identity and identity in {c.name for c in columns}:
        return identity
    return _identity_column(None, columns)


def _declared_fk_sources(by_name: dict[str, Node], cols_of: dict[str, list[Node]],
                         from_concept: str, to_concept: str) -> list[tuple[str, str]]:
    """Every mart holding a column declared `links_to: <to_concept>`.

    A mart declared as some other concept is skipped: its key relates through a
    different relation. A mart that declares no concept is kept — a derived fact
    keyed on a commodity joins to the commodity whatever it is called.
    """
    out: list[tuple[str, str]] = []
    for name, m in by_name.items():
        declared = m.props.get("concept")
        if declared and declared != from_concept:
            continue
        out += [(name, c.name) for c in cols_of[name]
                if c.props.get("links_to") == to_concept
                and c.props.get("role") not in ("natural_key", "surrogate_key")]
    return out


def _names_concept(model_name: str, concept: str) -> bool:
    """Whether a model's name mentions a concept, singular or plural."""
    stem = concept.lower()
    forms = {stem, f"{stem}s", f"{stem}es"}
    if stem.endswith("y"):
        forms.add(f"{stem[:-1]}ies")
    return any(f in model_name.lower() for f in forms)


def _model_for_concept(g, by_name: dict[str, Node], concept: str,
                       cols_of: dict[str, list[Node]],
                       prefer_dimension: bool = False) -> str | None:
    """Which exposed model instantiates a concept, when nothing was declared.

    Raw tables carry the `instantiates` edge; marts inherit the concept through
    lineage. Prefer a mart whose name mentions the concept — a dimension first
    when resolving the entity side — else the first mart downstream of a table
    that instantiates it.
    """
    named = [name for name in by_name if _names_concept(name, concept)]
    if prefer_dimension:
        named = [n for n in named if n.startswith("dim_")] or named
    if named:
        return named[0]
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
