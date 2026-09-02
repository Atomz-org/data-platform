"""Render context cards — the always-in-context index.

These are token-budgeted by design. `pf tokens` fails CI if a card exceeds its
budget, because the always-on tier is what silently inflates every session.
"""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import yaml

from pf.kg.store import Node, open_graph

PROJECT_CARD_BUDGET = 1500
GROUP_CARD_BUDGET = 400


COVERAGE_KINDS = ("feeds", "measures")


def _uncovered_tables(g, tables: list[Node]) -> list[str]:
    """Raw tables from which no Metric is reachable.

    This walks the graph rather than comparing names. The previous version asked
    whether some metric name started with the table name's first six characters,
    so `charges` never matched `revenue` and the card claimed a coverage gap that
    did not exist — a false warning sitting in every session's always-on context.
    """
    out: list[str] = []
    for t in tables:
        seen = {t.id}
        frontier = [t.id]
        covered = False
        while frontier and not covered:
            nxt: list[str] = []
            for node_id in frontier:
                for e in g.out_edges(node_id):
                    if e.kind not in COVERAGE_KINDS or e.dst in seen:
                        continue
                    seen.add(e.dst)
                    target = g.node(e.dst)
                    if target and target.kind == "Metric":
                        covered = True
                        break
                    nxt.append(e.dst)
                if covered:
                    break
            frontier = nxt
        if not covered:
            out.append(t.name)
    return sorted(out)


#: Tag namespaces worth rolling a large section up by, best first. Conventional
#: `key:value` dbt tags; a project without them falls back to a plain count.
ROLLUP_KEYS = ("domain", "type", "criticality", "layer")


def _tag_groups(nodes: list[Node], key: str) -> Counter:
    groups: Counter = Counter()
    for n in nodes:
        for tag in n.props.get("tags") or []:
            prefix, _, value = str(tag).partition(":")
            if prefix == key and value:
                groups[value] += 1
    return groups


def _summarise(nodes: list[Node]) -> str:
    """What the models that did not fit are, rather than only how many.

    The truncation these cards already do is what keeps them inside budget at any
    project size. What it does not do is stay *informative*: "…and 760 more" tells
    a reader nothing about a project whose shape is the thing they needed. Rolling
    the remainder up by tag costs a line and describes all of them.
    """
    for key in ROLLUP_KEYS:
        groups = _tag_groups(nodes, key)
        # One group is not a grouping, and it says less than the count did.
        if len(groups) > 1:
            shown = ", ".join(f"{v} ({n})" for v, n in groups.most_common(8))
            rest = len(groups) - 8
            return f"by {key}: {shown}" + (f", +{rest} more" if rest > 0 else "")
    return ""


def _bullets(nodes: list[Node], fmt, limit: int = 12) -> list[str]:
    ordered = sorted(nodes, key=lambda n: n.name)
    out = [fmt(n) for n in ordered[:limit]]
    if len(nodes) > limit:
        rollup = _summarise(ordered[limit:])
        tail = f" — {rollup}" if rollup else ""
        out.append(f"- …and {len(nodes) - limit} more{tail} (use `kg_search`)")
    return out


def _capped(values, limit: int, label: str = "") -> str:
    """Join a list, saying how many were left out rather than dropping them.

    Every list on a card needs a ceiling. A section that grows with the project
    is the one that silently pushes an otherwise fine card over budget, and the
    project it happens to is the large one nobody wants to debug.
    """
    values = list(values)
    head = ", ".join(str(v) for v in values[:limit])
    if len(values) <= limit:
        return head or "none"
    return f"{head}, +{len(values) - limit} more{f' {label}' if label else ''}"


def render_project_card(project_dir: str | Path, group: str, project: str) -> Path:
    root = Path(project_dir)
    graph_path = root / "kg" / "graph.duckdb"

    with open_graph(graph_path, read_only=True) as g:
        tables = g.nodes("Table")
        models = g.nodes("Model")
        metrics = g.nodes("Metric")
        dims = g.nodes("Dimension")
        exposures = g.nodes("Exposure")
        columns = g.nodes("Column")
        uncovered = _uncovered_tables(g, tables)

    used_concepts = sorted({t.props.get("concept") for t in tables if t.props.get("concept")})
    sources = sorted({t.props.get("source") for t in tables if t.props.get("source")})
    marts = [m for m in models if m.layer == "marts"]
    staging = [m for m in models if m.layer == "staging"]
    pii = [c for c in columns if c.props.get("pii")]

    gaps: list[str] = []
    if not metrics:
        gaps.append("no metrics defined — every business question falls back to raw SQL")
    if metrics and uncovered:
        gaps.append(f"{len(uncovered)} raw table(s) reach no metric: "
                    + _capped((f"`{n}`" for n in uncovered), 10))
    if not exposures:
        gaps.append("no exposures declared — impact analysis stops at the mart")

    lines = [
        f"## {project} — data index (generated {datetime.now(UTC).date().isoformat()})",
        "",
        f"**Group:** {group} · **Concepts in use:** {_capped(used_concepts, 15)}",
        f"**Sources ({len(sources)}):** {_capped(sources, 12)}",
        "",
        f"**Raw tables ({len(tables)}):**",
    ]
    lines += _bullets(tables, lambda n: f"- `{n.name}` → {n.props.get('concept','?')}"
                                        + (f" — {n.props.get('grain')}" if n.props.get("grain") else ""))
    lines += ["", f"**Staging models ({len(staging)}):** " +
              _capped((f"`{m.name}`" for m in sorted(staging, key=lambda n: n.name)), 15)]
    lines += ["", f"**Marts ({len(marts)}):**"]
    lines += _bullets(marts, lambda n: f"- `{n.name}`"
                                       + (f" — grain: {n.props.get('grain')}" if n.props.get("grain") else "")
                                       + (f" — {n.label}" if n.label else ""))
    lines += ["", f"**Metrics ({len(metrics)}):**"]
    lines += _bullets(metrics, lambda n: f"- `{n.name}` ({n.props.get('type','simple')})"
                                         + (f" — {n.label}" if n.label else ""), limit=20)
    if dims:
        lines += ["", f"**Common dimensions:** {_capped(sorted({d.name for d in dims}), 12)}"]
    if exposures:
        lines += ["", f"**Exposures ({len(exposures)}):**"]
        lines += _bullets(exposures, lambda n: f"- `{n.name}` ({n.props.get('type')}) "
                                               f"← {n.props.get('owner','unowned')}")
    if pii:
        lines += ["", f"**PII columns ({len(pii)}):** " + _capped(
            sorted(f"{c.props.get('table') or c.props.get('model')}.{c.name}" for c in pii), 10)]
    if gaps:
        lines += ["", "**Known gaps:**"] + [f"- {g}" for g in gaps]

    lines += [
        "",
        "_Query the graph before reading files: `kg_search`, `kg_neighbors`, `kg_path`._",
    ]

    out = root / "kg" / "context_card.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def render_group_card(group_dir: str | Path, group: str) -> Path:
    root = Path(group_dir)
    projects_dir = root / "projects"
    projects = sorted(p.name for p in projects_dir.iterdir()
                      if p.is_dir() and not p.name.startswith(".")) if projects_dir.exists() else []

    instance_path = root / "ontology" / "instance.yaml"
    instance = yaml.safe_load(instance_path.read_text(encoding="utf-8")) if instance_path.exists() else {}
    classes = instance.get("classes") or []
    shared = instance.get("shared_sources") or []

    lines = [
        f"## {group} — group index (generated {datetime.now(UTC).date().isoformat()})",
        "",
        f"**Sister projects ({len(projects)}):** " + (", ".join(f"`{p}`" for p in projects) or "none"),
        f"**Ontology classes in scope:** {', '.join(classes) or 'none'}",
    ]
    if shared:
        lines.append(f"**Shared sources:** {', '.join(shared)}")
    lines += [
        "",
        ("Sisters share the ontology, conformed dimensions and group metrics, but have "
         "separate warehouses and run in parallel. Cross-entity questions are answered "
         "only in the `<group>-rollup` project, which attaches sister databases READ_ONLY."),
        "",
        ("**Do not read a sister project's files from here.** If you need cross-entity "
         "data, use the rollup project."),
    ]
    out = root / "kg" / "group_card.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def estimate_tokens(text: str) -> int:
    """Rough local estimate. `pf tokens --exact` uses the Anthropic count_tokens API."""
    return max(1, len(text) // 4)
