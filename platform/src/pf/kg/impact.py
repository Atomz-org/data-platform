"""Blast-radius analysis. The merge gate that makes agentic change safe.

Given a node (or a set of changed dbt nodes), walk the graph downstream and
report every model, metric, dimension, exposure and test that would be affected
— plus the human who owns each exposure.

Scope is one project. Graphs are per-project and hold no cross-project edges, so
a sister's dependency on a change here is *not* visible: sisters share the group
ontology, not a graph. Cross-entity blast radius has to be assessed in the
`<group>-rollup` project, against its own graph.
"""

from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

from pf.kg.store import Graph, Node, open_graph

# Edges that carry impact downstream. `has_column` is walked upward instead, so
# that changing a column implicates its parent model.
DOWNSTREAM_KINDS = {"feeds", "measures", "grouped_by", "tested_by"}
UPWARD_KINDS = {"has_column"}

SEVERITY_ORDER = {"breaking": 0, "review": 1, "safe": 2}


@dataclass
class ImpactReport:
    root: str
    root_kind: str
    models: list[Node] = field(default_factory=list)
    metrics: list[Node] = field(default_factory=list)
    exposures: list[Node] = field(default_factory=list)
    tests: list[Node] = field(default_factory=list)
    dimensions: list[Node] = field(default_factory=list)
    owners: list[str] = field(default_factory=list)
    severity: str = "safe"

    @property
    def total(self) -> int:
        return len(self.models) + len(self.metrics) + len(self.exposures) + len(self.dimensions)

    def to_dict(self) -> dict:
        def pack(ns: list[Node]) -> list[dict]:
            return [{"id": n.id, "name": n.name, "layer": n.layer, "label": n.label,
                     "props": n.props} for n in ns]
        return {
            "root": self.root, "root_kind": self.root_kind, "severity": self.severity,
            "total": self.total, "owners": self.owners,
            "models": pack(self.models), "metrics": pack(self.metrics),
            "exposures": pack(self.exposures), "tests": pack(self.tests),
            "dimensions": pack(self.dimensions),
        }

    def render(self) -> str:
        if self.total == 0:
            return f"✅ No downstream dependencies on {self.root}. Safe to change."

        icon = {"breaking": "⛔", "review": "⚠️ ", "safe": "✅"}[self.severity]
        lines = [
            f"{icon} Changing `{self.root}` ({self.root_kind}) affects "
            f"{self.total} downstream object(s) — severity: {self.severity.upper()}",
            "",
        ]
        def section(title: str, ns: list[Node]) -> None:
            if not ns:
                return
            lines.append(f"{title} ({len(ns)}):")
            for n in sorted(ns, key=lambda x: x.name):
                suffix = ""
                if n.kind == "Exposure":
                    owner = n.props.get("owner") or "unowned"
                    suffix = f"  ← owner: {owner} <{n.props.get('email') or 'n/a'}>"
                elif n.props.get("grain"):
                    suffix = f"  (grain: {n.props['grain']})"
                lines.append(f"  • {n.name}{suffix}")
            lines.append("")

        section("Models", self.models)
        section("Metrics", self.metrics)
        section("Dimensions", self.dimensions)
        section("Exposures", self.exposures)
        if self.tests:
            lines.append(f"Tests that will re-run: {len(self.tests)}")
            lines.append("")
        if self.exposures:
            lines.append("Notify the exposure owners above before merging.")
        return "\n".join(lines).rstrip()


def _classify(report: ImpactReport) -> str:
    if report.exposures or report.metrics:
        return "breaking"
    if report.models:
        return "review"
    return "safe"


def impact_of(graph_path: str | Path, node_id: str, max_depth: int = 12) -> ImpactReport:
    """Walk downstream from `node_id` and collect everything that depends on it."""
    with open_graph(graph_path, read_only=True) as g:
        root = g.node(node_id)
        if root is None:
            raise KeyError(f"node '{node_id}' not in graph")

        seen: set[str] = {node_id}
        q: deque[tuple[str, int]] = deque([(node_id, 0)])
        collected: list[Node] = []

        while q:
            cur, d = q.popleft()
            if d >= max_depth:
                continue
            # a column's parent model is implicated
            for e in g.in_edges(cur):
                if e.kind in UPWARD_KINDS and e.src not in seen:
                    seen.add(e.src)
                    n = g.node(e.src)
                    if n:
                        collected.append(n)
                        q.append((e.src, d + 1))
            for e in g.out_edges(cur):
                if e.kind in DOWNSTREAM_KINDS and e.dst not in seen:
                    seen.add(e.dst)
                    n = g.node(e.dst)
                    if n:
                        collected.append(n)
                        q.append((e.dst, d + 1))

        report = ImpactReport(root=node_id, root_kind=root.kind)
        for n in collected:
            match n.kind:
                case "Model":     report.models.append(n)
                case "Metric":    report.metrics.append(n)
                case "Exposure":  report.exposures.append(n)
                case "Test":      report.tests.append(n)
                case "Dimension": report.dimensions.append(n)

        report.owners = sorted({
            f"{n.props.get('owner')} <{n.props.get('email')}>"
            for n in report.exposures if n.props.get("owner")
        })
        report.severity = _classify(report)
        return report


def impact_of_many(graph_path: str | Path, node_ids: list[str]) -> ImpactReport:
    """Union impact across several changed nodes (e.g. `dbt ls -s state:modified`)."""
    merged = ImpactReport(root=", ".join(node_ids), root_kind="ChangeSet")
    seen: set[str] = set()
    for nid in node_ids:
        try:
            r = impact_of(graph_path, nid)
        except KeyError:
            continue
        for attr in ("models", "metrics", "exposures", "tests", "dimensions"):
            for n in getattr(r, attr):
                if n.id in seen:
                    continue
                seen.add(n.id)
                getattr(merged, attr).append(n)
    merged.owners = sorted({
        f"{n.props.get('owner')} <{n.props.get('email')}>"
        for n in merged.exposures if n.props.get("owner")
    })
    merged.severity = _classify(merged)
    return merged


class GateNotExercised(Exception):
    """The graph cannot answer the question the gate was asked."""


def gate(graph_path: str | Path, node_ids: list[str], fail_on: str = "breaking") -> tuple[int, str]:
    """CI entry point. Returns (exit_code, rendered_report).

    Raises `GateNotExercised` when the graph holds no models at all. That graph
    is what `pf kg build` produces from a project whose dbt manifest was never
    parsed, and every blast-radius query over it comes back empty — so the gate
    reports "safe to change" for a change it could not see, and passes. A gate
    that cannot answer has to say so; a green tick that means "found nothing"
    is worse than no gate, because it is trusted.
    """
    with open_graph(graph_path, read_only=True) as g:
        if not g.counts().get("Model"):
            raise GateNotExercised(
                f"{graph_path} holds no models — the dbt manifest was never "
                f"parsed, so a blast radius cannot be computed. Run "
                f"`pf kg build` (which parses first) before gating."
            )
    report = impact_of_many(graph_path, node_ids)
    threshold = SEVERITY_ORDER[fail_on]
    code = 1 if SEVERITY_ORDER[report.severity] <= threshold and report.total else 0
    return code, report.render()
