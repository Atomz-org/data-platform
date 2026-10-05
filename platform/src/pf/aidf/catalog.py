"""What a mart actually has, for the hallucination check.

The columns a metric may reference come from the entity's own knowledge graph —
the same `kg/graph.json` the impact gate and the context card read — so the
governance engine never has to be told a schema and never has to trust the
agent's account of one. Three sources, best first, each one tried only when the
one before is absent:

    kg/graph.duckdb                  the live graph, typed columns backfilled
                                     from the warehouse
    kg/graph.json                    the tracked export; what CI has
    transform/target/manifest.json   dbt's own view, when the graph has not
                                     been built yet

`None` means "no catalogue could be found", which the validator reports as
`catalog: absent` and does not treat as a pass — a check that could not run is
not a check that succeeded.
"""

from __future__ import annotations

import json
from pathlib import Path


def _graph_columns(graph, mart: str) -> set[str] | None:
    models = [m for m in graph.nodes("Model") if m.name.lower() == mart.lower()]
    if not models:
        return None
    cols: set[str] = set()
    for m in models:
        for e in graph.out_edges(m.id):
            n = graph.node(e.dst)
            if n is not None and n.kind == "Column" and n.name:
                # Column node names may be qualified (`model.column`); the last
                # segment is the column.
                cols.add(n.name.split(".")[-1].lower())
    return cols


def _graph_tables(graph) -> set[str]:
    return {m.name.lower() for m in graph.nodes("Model") if m.name}


def columns_for(project_dir: Path, mart: str) -> set[str] | None:
    """The mart's columns, lower-cased, or None when no catalogue is available."""
    kg = project_dir / "kg"
    duck = kg / "graph.duckdb"
    if duck.exists():
        try:
            from pf.kg.store import open_graph

            with open_graph(duck, read_only=True) as g:
                found = _graph_columns(g, mart)
                if found is not None:
                    return found
        except Exception:  # noqa: BLE001 — a locked or half-built graph falls through to the export
            pass
    export = kg / "graph.json"
    if export.exists():
        try:
            from pf.kg.store import open_export

            with open_export(export) as g:
                found = _graph_columns(g, mart)
                if found is not None:
                    return found
        except Exception:  # noqa: BLE001
            pass
    manifest = project_dir / "transform" / "target" / "manifest.json"
    if manifest.exists():
        try:
            nodes = json.loads(manifest.read_text(encoding="utf-8")).get("nodes", {})
        except (OSError, ValueError):
            return None
        for node in nodes.values():
            if node.get("resource_type") == "model" and node.get("name", "").lower() == mart.lower():
                cols = {c.lower() for c in (node.get("columns") or {})}
                return cols or None
    return None


def tables_for(project_dir: Path) -> set[str] | None:
    """Every model name the entity has, or None when no catalogue is available."""
    kg = project_dir / "kg"
    for path, opener in ((kg / "graph.duckdb", "open_graph"), (kg / "graph.json", "open_export")):
        if not path.exists():
            continue
        try:
            from pf.kg import store

            fn = getattr(store, opener)
            with (fn(path, read_only=True) if opener == "open_graph" else fn(path)) as g:
                tables = _graph_tables(g)
                if tables:
                    return tables
        except Exception:  # noqa: BLE001
            continue
    manifest = project_dir / "transform" / "target" / "manifest.json"
    if manifest.exists():
        try:
            nodes = json.loads(manifest.read_text(encoding="utf-8")).get("nodes", {})
        except (OSError, ValueError):
            return None
        tables = {n["name"].lower() for n in nodes.values()
                  if n.get("resource_type") in ("model", "seed", "snapshot") and n.get("name")}
        return tables or None
    return None
