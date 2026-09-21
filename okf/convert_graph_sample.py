#!/usr/bin/env python3
"""Convert jaffle-shop's real kg/graph.json Table layer into an OKF bundle.

Scope, deliberately: the *raw* layer only — 57 Table nodes, their columns,
their one Source, the ontology Concept each instantiates. That is 6.6% of the
graph by node count (57 of 4574) and the smallest of its 8 kinds by volume.
Even at this scope the file count already exceeds the entire docs/ bundle,
which is itself the finding — see okf/REPORT.md for what this means
extrapolated to the other 4517 nodes (1088 Models, 2392 Columns, 540 Tests,
298 Properties, 68 Concepts, 32 Policies, 25 Dimensions, 22 Exposures,
19 Metrics, 15 Evidence, 14 Relations).

Columns are embedded as a markdown schema table in each Table concept's body,
matching OKF's own reference convention (testdata/valid/tables/events_.md) —
not split into one file per column, which would be the unfair comparison.
"""

import json
import pathlib

import yaml

REPO = pathlib.Path(__file__).resolve().parent.parent
GRAPH = REPO / "groups" / "jaffle" / "projects" / "jaffle-shop" / "kg" / "graph.json"
OUT = REPO / "okf" / "bundles" / "graph-sample"
(OUT / "tables").mkdir(parents=True, exist_ok=True)
(OUT / "sources").mkdir(parents=True, exist_ok=True)

g = json.loads(GRAPH.read_text())
nodes = {n["id"]: n for n in g["nodes"]}
edges = g["edges"]

tables = [n for n in g["nodes"] if n["kind"] == "Table"]
contains = {e["dst"]: e["src"] for e in edges if e["kind"] == "contains"}
instantiates = {e["src"]: e["dst"] for e in edges if e["kind"] == "instantiates"}
has_col = {}
for e in edges:
    if e["kind"] == "has_column":
        has_col.setdefault(e["src"], []).append(e["dst"])

# One Source concept (jaffle-shop's raw layer has exactly one: jaffle-seeds).
sources = sorted({contains[t["id"]] for t in tables if t["id"] in contains})
for sid in sources:
    sn = nodes.get(sid, {"name": sid, "props": {}})
    fm = {
        "type": "Source",
        "title": sn.get("name", sid),
        "description": f"dlt/dbt source node `{sid}` from jaffle-shop's committed graph.",
        "tags": ["jaffle-shop", "raw", "graph-sample"],
        "status": "stable",
    }
    body = f"# {sn.get('name', sid)}\n\nProps: `{sn.get('props', {})}`\n"
    p = OUT / "sources" / f"{sid.split(':')[-1].replace('.', '-')}.md"
    p.write_text(f"---\n{yaml.safe_dump(fm, sort_keys=False)}---\n\n{body}", encoding="utf-8")

rows = []
for t in tables:
    tid = t["id"]
    cols = []
    for cid in has_col.get(tid, []):
        cn = nodes.get(cid, {})
        props = cn.get("props", {})
        cols.append((cn.get("name", cid.split(".")[-1]), props.get("data_type", "?"), props.get("role", "")))
    src_id = contains.get(tid)
    concept_id = instantiates.get(tid)
    schema_rows = "\n".join(f"| `{n}` | {ty} | {role} |" for n, ty, role in cols)
    body = (
        f"# Schema\n\n"
        f"| Column | Type | Role |\n|---|---|---|\n{schema_rows}\n\n"
        f"# Provenance\n\n"
        f"Instantiates ontology concept `{concept_id}`. "
        f"Sourced from [{src_id}](/sources/{src_id.split(':')[-1].replace('.', '-')}.md).\n"
    )
    fm = {
        "type": "Table",
        "title": t.get("name", tid),
        "description": t.get("label", "") or f"Table {t.get('name')} in the raw layer.",
        "tags": ["jaffle-shop", t.get("layer", "raw"), "graph-sample"],
        "status": "stable",
    }
    out_path = OUT / "tables" / f"{tid.split(':')[-1].replace('.', '-')}.md"
    out_path.write_text(f"---\n{yaml.safe_dump(fm, sort_keys=False)}---\n\n{body}", encoding="utf-8")
    rows.append((tid, len(cols)))

total_bytes = sum(p.stat().st_size for p in (OUT / "tables").glob("*.md")) + sum(
    p.stat().st_size for p in (OUT / "sources").glob("*.md")
)
print(f"{len(rows)} Table concepts, {len(sources)} Source concept(s)")
print(f"total bundle size: {total_bytes} bytes ({total_bytes / len(rows):.0f} bytes/table avg)")
print(f"committed kg/graph.json for comparison: {GRAPH.stat().st_size} bytes, 1 file, {len(g['nodes'])} nodes total")
