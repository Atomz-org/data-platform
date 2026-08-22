"""Lint mermaid before a reader finds it broken.

A mermaid diagram fails in one direction only, and it fails quietly: GitHub
renders a source it cannot parse as a red box, and every job around it still
exits 0. The failure modes below are the ones that produce a *wrong* diagram
rather than an obvious one — the worst kind, because the page still looks fine.

  edge to an undeclared node   mermaid invents an empty box and draws to it
  a duplicated node id         mermaid merges them, so one layer vanishes
  a class that was never       the node keeps the default fill, which is the
    defined                      yellow that reads as a warning
  a raw `<` in a label         htmlLabels is on, so `Name <addr>` has the
                                 address parsed as a tag and silently dropped

`platform/toolkits/viz-standards/skills/charts-and-diagrams` is where these
rules come from; this is the executable half.
"""

from __future__ import annotations

import re

#: Lines that declare styling or structure rather than a node or an edge.
_NON_NODE = ("classDef", "class ", "style ", "%%", "flowchart", "graph",
             "subgraph", "direction", "end")

#: Every mermaid shape that declares a node: `[`, `(`, `[(`, `([`, `{`, `{{`.
_DECL = re.compile(r"(?<![\w\-])([A-Za-z_]\w*)\s*(?:\[\(|\(\[|\[|\(\(|\(|\{\{|\{)")

#: Label forms, longest first — a cylinder `[( )]` must be stripped before `[`.
_LABELS = (r"\[\([^)]*\)\]", r"\(\[[^\]]*\]\)", r"\[[^\]]*\]",
           r"\{\{[^}]*\}\}", r"\{[^}]*\}", r"\([^)]*\)")


def blocks(markdown: str) -> list[str]:
    """Every ```mermaid fence in a markdown document."""
    return re.findall(r"```mermaid\n(.*?)\n```", markdown, re.S)


def lint(block: str) -> list[str]:
    """Problems in one diagram. Empty means it parses and says what it looks like."""
    problems: list[str] = []
    lines = [line.strip() for line in block.splitlines()]

    declared: set[str] = set()
    duplicated: list[str] = []
    for s in lines:
        if s.startswith(_NON_NODE[:1] + _NON_NODE[1:6]):
            continue
        for m in _DECL.finditer(s):
            if m.group(1) in declared:
                duplicated.append(m.group(1))
            declared.add(m.group(1))
        sub = re.match(r"subgraph\s+([A-Za-z_]\w*)", s)
        if sub:
            declared.add(sub.group(1))

    # Strip labels, then normalise every edge form to `-->` so the endpoints are
    # all that is left. `-.text.->` is the one that defeats a naive scan: the
    # label lives *inside* the operator rather than in brackets.
    referenced: set[str] = set()
    for s in lines:
        if s.startswith(_NON_NODE):
            continue
        t = s
        for pat in _LABELS:
            t = re.sub(pat, "", t)
        t = re.sub(r"-\.[^.>]*\.->", " --> ", t)
        t = re.sub(r"-\.->", " --> ", t)
        t = re.sub(r"-->\s*\|[^|]*\|", " --> ", t)
        if "-->" not in t:
            continue
        for part in t.split("-->"):
            tok = part.strip()
            if re.fullmatch(r"[A-Za-z_]\w*", tok):
                referenced.add(tok)

    defined_classes = set(re.findall(r"classDef\s+(\w+)", block))
    used_classes: set[str] = set()
    for m in re.finditer(r"^\s*class\s+([\w,]+)\s+(\w+)\s*$", block, re.M):
        used_classes.add(m.group(2))
        problems += [f"class targets undeclared node '{n}'"
                     for n in m.group(1).split(",") if n and n not in declared]

    styled = set(re.findall(r"^\s*style\s+(\w+)", block, re.M))

    problems += [f"edge to undeclared node '{n}'" for n in sorted(referenced - declared)]
    problems += [f"duplicate node id '{n}' — mermaid merges these silently"
                 for n in sorted(set(duplicated))]
    problems += [f"class '{c}' used but never defined" for c in sorted(used_classes - defined_classes)]
    problems += [f"style targets undeclared node '{s}'" for s in sorted(styled - declared)]
    problems += [f"unescaped '<' in label (htmlLabels drops it): {lab[:48]}"
                 for lab in re.findall(r'\["([^"]*)"\]', block)
                 if re.search(r"<(?!br\s*/?>)", lab)]
    return problems
