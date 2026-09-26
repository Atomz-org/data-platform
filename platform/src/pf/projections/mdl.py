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

Read from the graph the project committed, not from the one on this machine.
`kg/graph.duckdb` is gitignored; `kg/graph.json` is the same graph, written by
`pf kg build` on the way out and committed beside the manifest. Building from
the database when it is there and from the export when it is not makes the
manifest reproducible in a bare clone — and makes `check_manifest` possible at
all: the committed manifest is compared against a projection of the committed
graph, rebuilding neither.

Which *mart* plays each side is read from what the project declared — a model's
`meta.concept` and a column's `meta.links_to` — before any naming heuristic.
The heuristic alone matched `commodity` against `fct_commodity_prices_daily`
rather than `dim_commodities`, joined the fact to itself, and dropped the
relationship without a word.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pf.kg.store import Node, open_export, open_graph
from pf.ontology.model import load_group_ontology, load_ontology

# MDL schema types this as an integer, not a semver string.
LAYOUT_VERSION = 1
JOIN_TYPES = {"ONE_TO_ONE", "ONE_TO_MANY", "MANY_TO_ONE", "MANY_TO_MANY"}


def _source(root: Path, tracked: bool = False):
    """The graph to read: the database, or the export committed beside it.

    `tracked` forces the export, which is what a check needs — comparing a
    committed manifest against a projection of whatever the local warehouse
    happens to hold would pass or fail on a fact about this machine.

    Without it the database wins when it exists (it is what the last build
    wrote) and the export stands in when it does not, so `pf semantic mdl` works
    in a clone that has never built anything. When neither exists the database
    is opened anyway and DuckDB creates it empty — the long-standing behaviour,
    and the projection of an empty graph is an empty manifest.
    """
    export = root / "kg" / "graph.json"
    db = root / "kg" / "graph.duckdb"
    if tracked or (not db.is_file() and export.is_file()):
        return open_export(export)
    return open_graph(db, read_only=True)


def exposed_models(g, layer: str = "marts") -> list[Node]:
    """Which models the semantic layer exposes.

    The marts layer, minus what the project marked `semantic: false`, plus what
    it marked `semantic: true` and any mart an exposure names.

    The layer alone was the whole rule, and it cannot tell a BI surface from a
    corpus: an adopted repository with 996 models under `marts/` projected all
    996, which is a manifest no one can read and a knowledge bundle the OKF spec
    refuses to hold. So the project declares, in dbt `meta` where the model is —
    and an exposure counts as a declaration, because naming a model in one is
    the project stating that people consume it.

    Nothing shrinks by default: a project that declares no `semantic` key gets
    the layer it always got.
    """
    named = {e.src for e in g.edges() if e.kind == "feeds" and e.dst.startswith("exposure:")}
    out = []
    for m in g.nodes("Model"):
        declared = m.props.get("semantic")
        if declared is True:
            out.append(m)  # declared in, whatever layer it sits in
        elif m.layer == layer and (declared is None or m.id in named):
            out.append(m)
    return out


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
                   layer: str = "marts", tracked: bool = False) -> dict[str, Any]:
    """Build an MDL manifest from one project's graph.

    Only `marts` are exposed by default — staging is an implementation detail,
    and a semantic layer that exposes it invites the exact ad-hoc SQL the metrics
    layer exists to prevent — and a project narrows or widens that with the
    `semantic` flag in dbt `meta`. See `exposed_models`.
    """
    root = Path(project_dir)
    onto = _ontology(root, group)

    models: list[dict[str, Any]] = []
    relationships: list[dict[str, Any]] = []
    cubes: list[dict[str, Any]] = []
    enum_definitions: list[dict[str, Any]] = []

    with _source(root, tracked) as g:
        wanted = exposed_models(g, layer)
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
        # One cube per model that carries metrics, holding only what that
        # model can answer. A cube has one base object, and the engine reads
        # every bare name in a measure against it: a single project-wide cube
        # based on the busiest mart hands it `sum(duty_local)` for a column
        # that lives on another fact, which plans against the wrong table or
        # not at all. So each metric goes to its home model (the model that
        # `measures` it; a ratio's home is its numerator's and denominator's,
        # when they agree), each dimension to the models it is declared on,
        # and a measure that names anything the base does not have is left
        # out rather than approximated.
        metrics = g.nodes("Metric")
        if metrics:
            by_metric = {mt.name: mt for mt in metrics}
            home = _metric_homes(g, metrics, by_name)
            dims_of = _dimensions_by_model(g, by_name)
            for base in sorted({h for h in home.values() if h}):
                base_columns = {c.name for c in cols_of.get(base, [])}
                # A measure named like a column of the base object shadows that
                # column inside the cube: `sum(order_cost)` in a measure called
                # `order_cost` reads the measure, not the column, and the engine
                # reports a circular dependency. Qualifying the column by the base
                # object (`sum(orders.order_cost)`) is what the engine resolves
                # correctly, and it keeps the governed name on the measure.
                shadowed = {name for name in by_metric if name in base_columns}
                candidates: list[tuple[Node, str]] = []
                for mt in sorted((m for m in metrics if home.get(m.name) == base), key=lambda m: m.name):
                    expression = _measure_expression(mt, by_metric)
                    if expression is None:
                        # A cube measure is a SQL aggregate or it is nothing. A
                        # placeholder parses as a comment and the whole cube fails
                        # to analyse; a missing measure costs one metric.
                        continue
                    if _reads_only(expression, base_columns):
                        candidates.append((mt, expression))
                # The engine substitutes a measure for *any* identifier that
                # names one — a table qualifier included. So when a measure is
                # named like the base object itself (`orders` on `orders`), the
                # qualification above turns `sum(orders.order_cost)` into
                # `sum((sum(1)).order_cost)`: it plans, and the warehouse refuses
                # a nested aggregate. The base-named measure is the one left out,
                # since it is what makes the others inexpressible.
                names = {mt.name for mt, _ in candidates}
                needs_qualifier = any(_bare_names(e) & shadowed for _, e in candidates)
                if base in names and needs_qualifier:
                    candidates = [(mt, e) for mt, e in candidates if mt.name != base]
                    names.discard(base)
                measures = []
                for mt, expression in candidates:
                    for name in shadowed:
                        expression = re.sub(rf"(?<![\w.]){re.escape(name)}\b", f"{base}.{name}", expression)
                    if _names_a_measure(expression, names):
                        continue
                    measures.append({
                        "name": mt.name,
                        "expression": expression,
                        "type": "DOUBLE",
                        "description": mt.label or mt.props.get("description", ""),
                        "properties": {"pf.metric_type": mt.props.get("type", "simple")},
                    })
                if not measures:
                    continue
                # A dimension is declared once per semantic model; on this
                # cube only the ones its base declares and actually has.
                own = [d for d in dims_of.get(base, []) if d.name in base_columns]
                cubes.append({
                    "name": f"{base}_metrics",
                    "baseObject": base,
                    "measures": measures,
                    "dimensions": _dedupe_dims([d for d in own if d.props.get("type") != "time"], "VARCHAR"),
                    "timeDimensions": _dedupe_dims([d for d in own if d.props.get("type") == "time"], "TIMESTAMP"),
                })

        # -- enums, from status_enum columns ---------------------------------
        for m in wanted:
            for c in cols_of[m.name]:
                if c.props.get("role") == "status_enum" and c.props.get("values"):
                    enum_definitions.append({
                        "name": f"{m.name}_{c.name}",
                        "values": [{"name": v, "value": v} for v in c.props["values"]],
                    })

    catalog = group.replace("-", "_")
    schema = project.replace("-", "_")
    manifest: dict[str, Any] = {
        "catalog": catalog,
        "schema": schema,
        "dataSource": "DUCKDB",
        "layoutVersion": LAYOUT_VERSION,
        "models": models,
        "relationships": relationships,
        "views": _views(root, models, relationships, tracked),
        "cubes": cubes,
    }
    if enum_definitions:
        manifest["enumDefinitions"] = enum_definitions
    return manifest


#: A bare identifier: not the qualifier before a dot, not the name after one,
#: not a function being called.
_IDENT = re.compile(r"(?<![\w.])[a-z_][a-z0-9_]*\b(?!\s*[.(])")
#: SQL words `agg_sql` can emit around a column. Anything else bare is a name
#: the base object has to have.
_SQL_WORDS = frozenset({
    "distinct", "case", "when", "then", "else", "end", "and", "or", "not", "null", "is", "in",
    "as", "true", "false", "between", "like", "within", "group", "order", "by", "asc", "desc",
    "filter", "where", "cast", "interval",
})


def _reads_only(expression: str, base_columns: set[str]) -> bool:
    """Does every name this measure reads exist on the cube's base object?

    Inside a cube a bare identifier resolves against the cube's own measures
    first and the base object's columns second, so a name the base lacks is at
    best an error and at worst the measure reading itself (Wren's "circular
    dependency"). String literals are not names.
    """
    text = re.sub(r"'(?:[^']|'')*'", "''", expression.lower())
    return all(name in base_columns or name in _SQL_WORDS for name in _IDENT.findall(text))


def _bare_names(expression: str) -> set[str]:
    """The column names a measure reads unqualified (string literals aside)."""
    text = re.sub(r"'(?:[^']|'')*'", "''", expression.lower())
    return set(_IDENT.findall(text)) - _SQL_WORDS


#: Any identifier the engine could read as a measure: a bare name or a
#: qualifier, but not the column after a dot and not a function being called.
_ANY_NAME = re.compile(r"(?<![\w.])[a-z_][a-z0-9_]*\b(?!\s*\()")


def _names_a_measure(expression: str, measures: set[str]) -> bool:
    """Does this measure, as emitted, contain a name the cube resolves to a
    measure — itself included, which is Wren's "circular dependency"?"""
    text = re.sub(r"'(?:[^']|'')*'", "''", expression.lower())
    return bool(set(_ANY_NAME.findall(text)) & measures)


def _metric_homes(g, metrics: list[Node], by_name: dict[str, Node]) -> dict[str, str | None]:
    """The exposed model each metric is measured on, or None when it has none.

    A simple metric's home is the model with a `measures` edge to it. A ratio
    lives where both its sides live; a ratio across two models has no single
    base object and so no cube (MetricFlow still answers it).
    """
    home: dict[str, str | None] = {}
    for mt in metrics:
        sources = (g.node(e.src) for e in g.in_edges(mt.id) if e.kind == "measures")
        owners = sorted({n.name for n in sources if n and n.kind == "Model" and n.name in by_name})
        home[mt.name] = owners[0] if len(owners) == 1 else None
    for mt in metrics:
        if home.get(mt.name) is None and (mt.props.get("type") or "").lower() == "ratio":
            num = home.get(mt.props.get("numerator") or "")
            den = home.get(mt.props.get("denominator") or "")
            home[mt.name] = num if num and num == den else None
    return home


def _dimensions_by_model(g, by_name: dict[str, Node]) -> dict[str, list[Node]]:
    """Each exposed model's declared dimensions, from its `grouped_by` edges."""
    out: dict[str, list[Node]] = {}
    for name, m in by_name.items():
        out[name] = sorted((n for n in (g.node(e.dst) for e in g.out_edges(m.id))
                            if n and n.kind == "Dimension"), key=lambda d: d.name)
    return out


def _measure_expression(metric: Node, by_metric: dict[str, Node]) -> str | None:
    """SQL for one cube measure, or None when the metric is not one aggregate.

    A simple metric is its measure's aggregate. A ratio is its numerator over its
    denominator, re-divided rather than averaged — the same rule the reporting
    layer enforces, for the same reason: an average of averages weights a thin
    day like a full one, and for this platform's commodity groups a price is a
    unit price that must never be summed across rows.

    Derived and cumulative metrics carry window and offset semantics that a cube
    measure cannot express. They are omitted rather than approximated.
    """
    from pf.projections.evidence import agg_sql

    def aggregate(node: Node | None) -> str | None:
        if node is None or not node.props.get("agg"):
            return None
        return agg_sql(node.props["agg"], node.props["expr"],
                       node.props.get("agg_params") or {})

    kind = (metric.props.get("type") or "simple").lower()
    if kind == "simple":
        return aggregate(metric)
    if kind == "ratio":
        num = aggregate(by_metric.get(metric.props.get("numerator") or ""))
        den = aggregate(by_metric.get(metric.props.get("denominator") or ""))
        if num and den:
            return f"{num} / nullif({den}, 0)"
    return None


def _dedupe_dims(dims: list[Node], sql_type: str) -> list[dict[str, Any]]:
    """Fold dimensions that appear on more than one semantic model into one."""
    folded: dict[str, dict[str, Any]] = {}
    for d in dims:
        entry = folded.get(d.name)
        if entry is None:
            folded[d.name] = {"name": d.name, "expression": d.name,
                              "type": sql_type, "description": d.label or ""}
        elif not entry["description"] and d.label:
            entry["description"] = d.label
    return list(folded.values())


def _views(root: Path, models: list[dict[str, Any]],
           relationships: list[dict[str, Any]], tracked: bool = False) -> list[dict[str, Any]]:
    """One view per mart a dbt exposure names.

    An exposure is the only place in the stack where someone states *this is a
    surface people consume*. Deriving views from it keeps the same discipline as
    the relationships above: a projection of a declaration, never a guess from a
    name prefix. A view denormalises the mart along the relationships already
    derived — which is the point of having derived them — so the NL layer gets a
    question-shaped surface instead of a join it has to reconstruct.

    Columns from a joined model are prefixed with that model's name when the
    bare name would collide, because a view with two `commodity_id` columns is
    not a surface anyone can query.
    """
    by_name = {m["name"]: m for m in models}
    views: list[dict[str, Any]] = []

    with _source(root, tracked) as g:
        exposures = g.nodes("Exposure")
        if not exposures:
            return []
        feeds: dict[str, list[str]] = {}
        for e in g.edges():
            if e.kind == "feeds" and e.dst.startswith("exposure:") \
                    and e.src.startswith("model:"):
                feeds.setdefault(e.dst.split(":", 1)[1], []).append(
                    e.src.split(":", 1)[1])

        # A mart is usually named by several exposures — a hand-written board and
        # the generated page for every metric that sits on it. That is one
        # surface with several readers, not several surfaces: keyed by exposure
        # it produced duplicate view names, which is the same flat-namespace
        # collision the cube had. Key by model, and carry the readers.
        readers: dict[str, list[Node]] = {}
        for exp in exposures:
            for model_name in feeds.get(exp.name, []):
                readers.setdefault(model_name, []).append(exp)

        for model_name, exps in sorted(readers.items()):
            model = by_name.get(model_name)
            if model is None:              # staging, or filtered out of the MDL
                continue
            stmt = _view_statement(model, by_name, relationships)
            if stmt is None:
                continue
            exps = sorted(exps, key=lambda n: n.name)
            owners = sorted({e.props.get("owner") or "" for e in exps} - {""})
            views.append({
                "name": f"{model_name}_view",
                "statement": stmt,
                "properties": {
                    "pf.exposures": ", ".join(e.name for e in exps),
                    "pf.exposure_types": ", ".join(
                        sorted({e.props.get("type") or "" for e in exps} - {""})),
                    "pf.owners": ", ".join(owners),
                    "pf.description": model["properties"].get("description", ""),
                    "pf.grain": model["properties"].get("grain", ""),
                },
            })
    return views


def _view_statement(model: dict[str, Any],
                    by_name: dict[str, dict[str, Any]],
                    relationships: list[dict[str, Any]]) -> str | None:
    """`select` for one view: the mart, left-joined to what it points at.

    Models are named **bare**, not `catalog.schema.model`. Both spellings parse
    and both plan without error, but the qualified one is passed through to the
    warehouse verbatim — so the planner emitted SQL selecting from a DuckDB
    catalog named after the group, and every query against a view died with
    `Catalog "commodity" does not exist`. Only the bare name is resolved back to
    a model and rewritten to its `tableReference`.
    """
    def visible(m: dict[str, Any]) -> list[str]:
        # isHidden is the MDL projection's PII flag. A view is a wider surface
        # than a model, so honouring it here is not belt-and-braces: it is the
        # only thing standing between a hidden column and an NL query that
        # selects it back out.
        return [c["name"] for c in m["columns"]
                if not c.get("isHidden") and not c.get("relationship")]

    base = model["name"]
    taken = set(visible(model))
    select = [f"{base}.{c}" for c in visible(model)]
    joins: list[str] = []

    for rel in relationships:
        if rel["models"][0] != base or rel["joinType"] not in ("MANY_TO_ONE", "ONE_TO_ONE"):
            continue
        other = by_name.get(rel["models"][1])
        if other is None:
            continue
        joined = other["name"]
        for col in visible(other):
            alias = col if col not in taken else f"{joined.removeprefix('dim_')}_{col}"
            if alias in taken:
                continue
            taken.add(alias)
            select.append(f"{joined}.{col} as {alias}" if alias != col
                          else f"{joined}.{col}")
        joins.append(f"  left join {joined} on {rel['condition']}")

    if not select:
        return None
    body = ",\n".join(f"  {c}" for c in select)
    return (f"select\n{body}\nfrom {base}\n" + "\n".join(joins)).strip()


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


# ------------------------------------------------------------------ check ---
#: The manifest's list sections, each keyed by `name`.
SECTIONS = ("models", "relationships", "views", "cubes", "enumDefinitions")
#: The scalars at the top, which no list diff would mention.
HEADER = ("catalog", "schema", "dataSource", "layoutVersion")


@dataclass
class MdlDrift:
    """Is the committed manifest what the committed graph projects?

    The question `pf kg check` asks of the graph, asked one layer up. It was
    unanswerable while the projection could only read `kg/graph.duckdb`, which
    no clone has: the MDL was the only artefact in the chain that nothing
    compared, and both the India and US manifests had aged past the whole
    Evidence reporting layer before anyone noticed.

    `exercised` is the honest third answer, as everywhere else here: a project
    whose graph was never built cannot be judged, and calling that "current"
    would be the green tick for "found nothing".
    """

    project: str
    exercised: bool
    reason: str = ""
    missing: bool = False
    added: dict[str, list[str]] = field(default_factory=dict)
    removed: dict[str, list[str]] = field(default_factory=dict)
    changed: dict[str, list[str]] = field(default_factory=dict)
    header: list[str] = field(default_factory=list)
    unnamed: bool = False

    @property
    def total(self) -> int:
        counted = sum(len(v) for d in (self.added, self.removed, self.changed) for v in d.values())
        return counted + len(self.header) + int(self.unnamed) + int(self.missing)

    def render(self) -> str:
        if not self.exercised:
            return f"?  {self.project} — not exercised: {self.reason}"
        if self.missing:
            return f"⛔ {self.project} — no mdl/mdl.json; run `pf semantic mdl {self.project.replace('/', ' ')}`"
        if not self.total:
            return f"✓  {self.project} — manifest matches the graph"

        lines = [f"⛔ {self.project} — manifest is {self.total} change(s) behind the graph"]
        for label, entries, mark in (("missing", self.added, "+"), ("dropped", self.removed, "-"),
                                     ("stale", self.changed, "~")):
            for section, names in sorted(entries.items()):
                head = ", ".join(f"{mark}{n}" for n in sorted(names)[:6])
                rest = f", +{len(names) - 6} more" if len(names) > 6 else ""
                lines.append(f"     {section} {label}: {head}{rest}")
        if self.header:
            lines.append(f"     header: {', '.join(sorted(self.header))}")
        if self.unnamed:
            lines.append("     and a difference no section names — compare the file")
        lines.append(f"     run `pf semantic mdl {self.project.replace('/', ' ')}` and commit mdl/mdl.json")
        return "\n".join(lines)

    @property
    def problems(self) -> list[str]:
        return [self.render()] if self.exercised and self.total else []


def _by_name(manifest: dict[str, Any], section: str) -> dict[str, Any]:
    return {
        str(entry.get("name")): entry
        for entry in manifest.get(section) or []
        if isinstance(entry, dict) and entry.get("name")
    }


def check_manifest(project_dir: str | Path, group: str, project: str) -> MdlDrift:
    """Compare the committed manifest against a projection of the committed graph.

    Neither is rebuilt, and nothing here reads the warehouse or the graph
    database: this has to answer the same way on a laptop that has built
    everything and on a runner that has built nothing, or it is not a gate.
    """
    root = Path(project_dir)
    name = f"{group}/{project}"
    if not (root / "kg" / "graph.json").is_file():
        return MdlDrift(name, exercised=False,
                        reason="no kg/graph.json; the graph has never been built")
    path = root / "mdl" / "mdl.json"
    if not path.is_file():
        return MdlDrift(name, exercised=True, missing=True)
    try:
        committed_text = path.read_text(encoding="utf-8")
        committed = json.loads(committed_text)
    except ValueError as exc:
        return MdlDrift(name, exercised=True, reason=str(exc), unnamed=True)

    built = build_manifest(root, group, project, tracked=True)
    drift = MdlDrift(name, exercised=True)
    for section in SECTIONS:
        want, have = _by_name(built, section), _by_name(committed, section)
        if added := sorted(set(want) - set(have)):
            drift.added[section] = added
        if removed := sorted(set(have) - set(want)):
            drift.removed[section] = removed
        if changed := sorted(n for n in set(want) & set(have) if want[n] != have[n]):
            drift.changed[section] = changed
    drift.header = [k for k in HEADER if built.get(k) != committed.get(k)]
    # The sections above are what a person can act on; this is the backstop for
    # anything else — a key order, a section the manifest gained upstream —
    # so "current" always means byte-identical to what a rebuild would write.
    if not drift.total and committed_text != json.dumps(built, indent=2) + "\n":
        drift.unnamed = True
    return drift


def export(project_dir: str | Path, group: str, project: str,
           out: str | Path | None = None) -> Path:
    manifest = build_manifest(project_dir, group, project)
    path = Path(out) if out else Path(project_dir) / "mdl" / "mdl.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    from pf.kg.card import write_if_changed

    write_if_changed(path, json.dumps(manifest, indent=2) + "\n")
    return path
