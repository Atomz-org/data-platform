"""DuckDB-backed graph store. Two tables is enough.

EDGE DIRECTION IS A CONTRACT: every edge runs *upstream -> downstream*, so
`out_edges` is always "what depends on this". `feeds` is named for that
direction — a staging model feeds a mart. It was once called `derives_from`,
which read backwards in every rendered lineage path.

Only kinds that are actually emitted are listed here. A declared-but-unbuilt
kind is worse than no vocabulary: it makes traversals that filter on it look
implemented when they are dead.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import duckdb

NODE_KINDS = (
    # physical / analytical
    "Source", "Table", "Column", "Model", "Metric", "Dimension",
    "Test", "Exposure", "Project",
    # semantic (ontology + topology)
    "Concept", "Property", "Relation",
    # governance (OpenTopology: intent -> constraint -> artifact -> evidence)
    "Policy", "Evidence",
)
EDGE_KINDS = (
    # lineage — always upstream -> downstream
    "feeds", "measures", "grouped_by", "tested_by", "has_column", "contains",
    # semantics
    "instantiates",   # Table/Model -> Concept
    "has_property",   # Concept -> Property
    "domain_of",      # Concept -> Relation   (relation starts here)
    "range_of",       # Relation -> Concept   (relation ends here)
    "realises",       # Column -> Relation    (the physical FK behind a relation)
    "links_to",       # Column -> Concept     (declared target of a foreign key)
    # governance
    "governs",        # Policy -> anything it constrains
    "evidenced_by",   # Policy -> Evidence
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS kg_nodes (
    id      TEXT PRIMARY KEY,
    kind    TEXT NOT NULL,
    name    TEXT NOT NULL,
    layer   TEXT,
    label   TEXT,
    props   JSON
);
CREATE TABLE IF NOT EXISTS kg_edges (
    src     TEXT NOT NULL,
    dst     TEXT NOT NULL,
    kind    TEXT NOT NULL,
    props   JSON
);
CREATE INDEX IF NOT EXISTS kg_edges_src ON kg_edges(src);
CREATE INDEX IF NOT EXISTS kg_edges_dst ON kg_edges(dst);
CREATE INDEX IF NOT EXISTS kg_nodes_kind ON kg_nodes(kind);
"""


@dataclass
class Node:
    id: str
    kind: str
    name: str
    layer: str = ""
    label: str = ""
    props: dict[str, Any] = field(default_factory=dict)


@dataclass
class Edge:
    src: str
    dst: str
    kind: str
    props: dict[str, Any] = field(default_factory=dict)


class Graph:
    """Thin wrapper over a DuckDB connection holding kg_nodes / kg_edges."""

    def __init__(self, con: duckdb.DuckDBPyConnection, read_only: bool = False) -> None:
        self.con = con
        if not read_only:  # DDL is rejected on a read-only attachment
            self.con.execute(SCHEMA)

    # -- writes --------------------------------------------------------------
    def reset(self) -> None:
        self.con.execute("DELETE FROM kg_edges")
        self.con.execute("DELETE FROM kg_nodes")

    def add_nodes(self, nodes: list[Node]) -> None:
        if not nodes:
            return
        self.con.executemany(
            "INSERT OR REPLACE INTO kg_nodes VALUES (?, ?, ?, ?, ?, ?)",
            [(n.id, n.kind, n.name, n.layer, n.label, json.dumps(n.props)) for n in nodes],
        )

    def add_edges(self, edges: list[Edge]) -> None:
        """Insert edges, de-duplicated on (src, dst, kind).

        kg_edges has no primary key, and the builders legitimately derive the
        same edge twice — a ratio metric naming the same measure as numerator
        and denominator, say. Left in, the duplicate inflates every count and
        double-weights any future edge-weighted traversal.
        """
        if not edges:
            return
        seen: set[tuple[str, str, str]] = set()
        rows = []
        for e in edges:
            key = (e.src, e.dst, e.kind)
            if key in seen:
                continue
            seen.add(key)
            rows.append((e.src, e.dst, e.kind, json.dumps(e.props)))
        self.con.executemany("INSERT INTO kg_edges VALUES (?, ?, ?, ?)", rows)

    # -- reads ---------------------------------------------------------------
    def node(self, node_id: str) -> Node | None:
        row = self.con.execute(
            "SELECT id, kind, name, layer, label, props FROM kg_nodes WHERE id = ?", [node_id]
        ).fetchone()
        return _row_to_node(row) if row else None

    def nodes(self, kind: str | None = None) -> list[Node]:
        if kind:
            rows = self.con.execute(
                "SELECT id, kind, name, layer, label, props FROM kg_nodes "
                "WHERE kind = ? ORDER BY name", [kind]
            ).fetchall()
        else:
            rows = self.con.execute(
                "SELECT id, kind, name, layer, label, props FROM kg_nodes ORDER BY kind, name"
            ).fetchall()
        return [_row_to_node(r) for r in rows]

    def edges(self) -> list[Edge]:
        rows = self.con.execute("SELECT src, dst, kind, props FROM kg_edges").fetchall()
        return [Edge(src=r[0], dst=r[1], kind=r[2], props=json.loads(r[3] or "{}")) for r in rows]

    def out_edges(self, node_id: str) -> list[Edge]:
        rows = self.con.execute(
            "SELECT src, dst, kind, props FROM kg_edges WHERE src = ?", [node_id]
        ).fetchall()
        return [Edge(src=r[0], dst=r[1], kind=r[2], props=json.loads(r[3] or "{}")) for r in rows]

    def in_edges(self, node_id: str) -> list[Edge]:
        rows = self.con.execute(
            "SELECT src, dst, kind, props FROM kg_edges WHERE dst = ?", [node_id]
        ).fetchall()
        return [Edge(src=r[0], dst=r[1], kind=r[2], props=json.loads(r[3] or "{}")) for r in rows]

    def counts(self) -> dict[str, int]:
        rows = self.con.execute(
            "SELECT kind, count(*) FROM kg_nodes GROUP BY kind ORDER BY 1"
        ).fetchall()
        return {r[0]: r[1] for r in rows}

    def close(self) -> None:
        self.con.close()


def _row_to_node(row: tuple) -> Node:
    return Node(
        id=row[0], kind=row[1], name=row[2], layer=row[3] or "",
        label=row[4] or "", props=json.loads(row[5] or "{}"),
    )


@contextmanager
def open_graph(path: str | Path, read_only: bool = False) -> Iterator[Graph]:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if read_only and not p.exists():
        read_only = False  # let duckdb create it rather than fail
    con = duckdb.connect(str(p), read_only=read_only)
    try:
        yield Graph(con, read_only=read_only)
    finally:
        con.close()
