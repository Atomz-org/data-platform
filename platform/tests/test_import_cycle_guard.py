"""The circular-import guard: pf's own import graph must stay acyclic.

Two layers guard the same invariant. This test is the hard wall — it walks
the real `import` statements of every module under `platform/src/pf` and
fails the suite (and with it the merge) on any cycle. The soft layer is the
git doctor's `import-cycle` finding, which reads the graphify knowledge graph
so the local model surfaces cycles during routine tree checks; its finder is
unit-tested here against a synthetic graph.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

from pf import gitdoctor

PF_ROOT = Path(__file__).resolve().parents[1] / "src" / "pf"


def _module_name(path: Path) -> str:
    rel = path.relative_to(PF_ROOT.parent).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _top_level(tree: ast.Module):
    """Module-level statements only, descending through top-level try/if.

    Function-scope imports are the sanctioned way to break a runtime cycle —
    this codebase uses them deliberately — so the wall counts only imports
    that execute at import time, the ones that can actually deadlock.
    """
    todo = list(tree.body)
    while todo:
        node = todo.pop()
        yield node
        if isinstance(node, (ast.Try, ast.If)):
            todo.extend(getattr(node, "body", []))
            todo.extend(getattr(node, "orelse", []))


def _pf_imports(path: Path, module: str) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: set[str] = set()
    for node in _top_level(tree):
        if isinstance(node, ast.Import):
            found.update(a.name for a in node.names if a.name.startswith("pf"))
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # relative import — resolve against this module
                base = module.rsplit(".", node.level)[0]
                found.add(f"{base}.{node.module}" if node.module else base)
            elif node.module and node.module.startswith("pf"):
                found.add(node.module)
    return found


def test_pf_module_import_graph_is_acyclic() -> None:
    modules = {}
    for path in PF_ROOT.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        name = _module_name(path)
        modules[name] = _pf_imports(path, name)

    # Edges resolve to the longest known module prefix, so
    # `from pf.runtime.quack import x` lands on pf.runtime.quack.
    def resolve(target: str) -> str | None:
        while target:
            if target in modules:
                return target
            target = target.rpartition(".")[0]
        return None

    def counts(m: str, r: str) -> bool:
        # A package __init__ re-exporting its child, and the child importing
        # siblings via the package, is the sanctioned partial-initialization
        # idiom — exempt direct parent<->child edges, catch everything else.
        return r != m and not r.startswith(m + ".") and not m.startswith(r + ".")

    graph = {m: {r for t in targets if (r := resolve(t)) and counts(m, r)} for m, targets in modules.items()}

    # Iterative DFS, module-level three-color.
    WHITE, GRAY, BLACK = 0, 1, 2
    color = dict.fromkeys(graph, WHITE)
    cycles: list[str] = []
    for start in sorted(graph):
        if color[start] != WHITE:
            continue
        stack: list[tuple[str, iter]] = [(start, iter(sorted(graph[start])))]
        path = [start]
        color[start] = GRAY
        while stack:
            node, it = stack[-1]
            for nxt in it:
                if color[nxt] == GRAY:
                    cycles.append(" -> ".join([*path[path.index(nxt) :], nxt]))
                elif color[nxt] == WHITE:
                    color[nxt] = GRAY
                    path.append(nxt)
                    stack.append((nxt, iter(sorted(graph[nxt]))))
                    break
            else:
                color[node] = BLACK
                stack.pop()
                if path and path[-1] == node:
                    path.pop()

    assert not cycles, "circular imports in pf:\n  " + "\n  ".join(sorted(set(cycles)))


def test_doctor_finds_cycles_in_a_knowledge_graph(tmp_path) -> None:
    out = tmp_path / "graphify-out"
    out.mkdir()
    out.joinpath("graph.json").write_text(
        json.dumps(
            {
                "nodes": [
                    {"id": "mod_a", "label": "a.py"},
                    {"id": "mod_b", "label": "b.py"},
                    {"id": "mod_c", "label": "c.py"},
                ],
                "links": [
                    {"source": "mod_a", "target": "mod_b", "relation": "imports"},
                    {"source": "mod_b", "target": "mod_a", "relation": "imports"},
                    # calls cycles are recursion, not architecture faults — ignored.
                    {"source": "mod_b", "target": "mod_c", "relation": "calls"},
                    {"source": "mod_c", "target": "mod_b", "relation": "calls"},
                ],
            }
        )
    )
    findings = gitdoctor.import_cycles(tmp_path)
    assert len(findings) == 1
    assert findings[0].kind == "import-cycle"
    assert "a.py" in findings[0].detail and "b.py" in findings[0].detail
    # leave-only on the menu: the model may never "fix" a cycle.
    assert gitdoctor.ALLOWED["import-cycle"] == ("leave",)


def test_doctor_cycle_finder_needs_no_graph(tmp_path) -> None:
    assert gitdoctor.import_cycles(tmp_path) == []
    (tmp_path / "graphify-out").mkdir()
    (tmp_path / "graphify-out" / "graph.json").write_text("not json")
    assert gitdoctor.import_cycles(tmp_path) == []
