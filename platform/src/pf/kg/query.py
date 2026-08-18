"""Graph queries. These back the MCP tools an agent calls *before* reading files.

All functions return compact strings: they are token-budgeted on purpose.
"""

from __future__ import annotations

from collections import deque
from pathlib import Path

from pf.kg.store import Node, open_graph

MAX_ROWS = 40


def _fmt(n: Node) -> str:
    bits = [f"{n.id}"]
    if n.layer:
        bits.append(f"[{n.layer}]")
    if n.label:
        bits.append(f"— {n.label[:80]}")
    extra = []
    if n.props.get("grain"):
        extra.append(f"grain={n.props['grain']}")
    if n.props.get("role"):
        extra.append(f"role={n.props['role']}")
    if n.props.get("pii"):
        extra.append("PII")
    if extra:
        bits.append(f"({', '.join(extra)})")
    return " ".join(bits)


def kg_search(graph_path: str | Path, term: str, kinds: list[str] | None = None,
              limit: int = MAX_ROWS) -> str:
    """Find nodes by name, label or business term. The vague-question entry point."""
    term_l = term.lower()
    with open_graph(graph_path, read_only=True) as g:
        hits = [
            n for n in g.nodes()
            if (term_l in n.name.lower() or term_l in n.label.lower()
                or term_l in n.id.lower())
            and (not kinds or n.kind in kinds)
        ]
    if not hits:
        return f"No nodes match '{term}'."
    hits.sort(key=lambda n: (n.kind, n.name))
    out = [f"{len(hits)} match(es) for '{term}'" + (f" (showing {limit})" if len(hits) > limit else "")]
    for n in hits[:limit]:
        out.append(f"  {n.kind:9} {_fmt(n)}")
    return "\n".join(out)


def kg_neighbors(graph_path: str | Path, node_id: str, depth: int = 1,
                 kinds: list[str] | None = None, limit: int = MAX_ROWS) -> str:
    """Explore the graph around a node. Call this before opening any file."""
    with open_graph(graph_path, read_only=True) as g:
        start = g.node(node_id)
        if start is None:
            near = kg_search(graph_path, node_id.split(":")[-1])
            return f"Node '{node_id}' not found.\n\nDid you mean:\n{near}"

        seen = {node_id}
        frontier = deque([(node_id, 0)])
        rows: list[tuple[int, str, str, Node]] = []

        while frontier:
            current, d = frontier.popleft()
            if d >= depth:
                continue
            for e in g.out_edges(current):
                nb = g.node(e.dst)
                if nb and e.dst not in seen:
                    seen.add(e.dst)
                    rows.append((d + 1, "→", e.kind, nb))
                    frontier.append((e.dst, d + 1))
            for e in g.in_edges(current):
                nb = g.node(e.src)
                if nb and e.src not in seen:
                    seen.add(e.src)
                    rows.append((d + 1, "←", e.kind, nb))
                    frontier.append((e.src, d + 1))

    if kinds:
        rows = [r for r in rows if r[3].kind in kinds]
    header = f"{start.kind} {_fmt(start)}\n{len(rows)} neighbour(s) within depth {depth}:"
    lines = [header]
    for d, arrow, kind, n in sorted(rows, key=lambda r: (r[0], r[3].kind))[:limit]:
        lines.append(f"  d{d} {arrow} {kind:12} {n.kind:9} {_fmt(n)}")
    if len(rows) > limit:
        lines.append(f"  … {len(rows) - limit} more (narrow with kinds=)")
    return "\n".join(lines)


def kg_path(graph_path: str | Path, src: str, dst: str, max_depth: int = 8) -> str:
    """Shortest lineage path — how does a source column reach a metric?"""
    with open_graph(graph_path, read_only=True) as g:
        if g.node(src) is None:
            return f"Source node '{src}' not found."
        if g.node(dst) is None:
            return f"Target node '{dst}' not found."

        prev: dict[str, tuple[str, str]] = {}
        seen = {src}
        q = deque([(src, 0)])
        found = False
        while q:
            cur, d = q.popleft()
            if cur == dst:
                found = True
                break
            if d >= max_depth:
                continue
            for e in g.out_edges(cur) + g.in_edges(cur):
                nxt = e.dst if e.src == cur else e.src
                if nxt not in seen:
                    seen.add(nxt)
                    prev[nxt] = (cur, e.kind)
                    q.append((nxt, d + 1))

        if not found:
            return f"No path from {src} to {dst} within {max_depth} hops."

        chain: list[str] = []
        cur = dst
        while cur != src:
            parent, kind = prev[cur]
            node = g.node(cur)
            chain.append(f"  --{kind}--> {node.kind} {cur}" + (f"  ({node.label[:60]})" if node.label else ""))
            cur = parent
        head = g.node(src)
        chain.append(f"{head.kind} {src}")
        return "\n".join(reversed(chain))


def summary(graph_path: str | Path) -> dict[str, int]:
    with open_graph(graph_path, read_only=True) as g:
        return g.counts()
