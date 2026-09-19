"""The diagram design system — one palette, one escape, one linter.

Three places in this repository render mermaid: the PR report (`pf.pr`), the
per-project architecture map (`pf.architecture`), and whatever ships next. A
palette copied into each is three palettes by the second release, and the one
that drifts is always the one nobody is looking at.

The rules encoded here come from the `viz-standards/charts-and-diagrams` skill,
and each exists because of a specific way a generated diagram fails:

**Pale fill, saturated stroke of the same hue, near-black ink.** GitHub renders
one mermaid source on both a light and a dark page and does *not* recolour an
explicit `classDef` fill. A saturated fill chosen against white is unreadable on
black, and there is no media query to rescue it. These fills are theme-invariant.

**Hue carries the job, never the rank.** `metric` is magenta in every diagram, so
a reader who has seen one of these has read all of them. The four status hues
(good / warning / critical, and their pale lane tints) are reserved: reusing one
for "the fourth thing" is how red stops meaning danger.

**Escaping is not optional.** `#` opens a mermaid entity reference and `"` closes
a label early — either turns the diagram into a parse error, which renders as a
red box while the job that produced it still exits 0. `<` is worse: `htmlLabels`
is on, so `Data Science <ds@x.test>` has the address parsed as a tag and
*silently dropped*, losing the very name a reader needed.

**Never derive a node id from data.** Two boxes sharing an id do not error —
mermaid merges them, and one layer quietly vanishes. Callers generate synthetic
ids; `lint` catches it when they forget.
"""

from __future__ import annotations

import re

#: Near-black label ink. Legible on every fill below, on either page theme.
INK = "#0b0b0b"

#: fill, stroke — keyed by the job the node does, never by what it is called in
#: any one diagram. Values are the set validated for the PR report (worst
#: measured text contrast 14.4:1); nothing here is a new hue.
PALETTE: dict[str, tuple[str, str]] = {
    "ingress": ("#cde2fb", "#2a78d6"),   # arrives from outside: a source, a PR
    "platform": ("#ded9f7", "#4a3aa7"),  # shared runtime, not this project's code
    "project": ("#e3eefc", "#2a78d6"),   # the entity itself
    "raw": ("#fbe8bd", "#eda100"),       # untransformed, or touched by a change
    "model": ("#d6f2e6", "#1baf7a"),     # dbt model
    "metric": ("#fadfe8", "#e87ba4"),    # governed quantity
    "exposure": ("#fbdccf", "#eb6834"),  # something a person reads
    "neutral": ("#e8e7e2", "#898781"),   # absent, or deliberately unremarkable
    "good": ("#d5f2d5", "#0ca30c"),      # -- reserved: status only --
    "warning": ("#fdeccb", "#fab219"),
    "critical": ("#f6d8d8", "#d03b3b"),
    # Container fills, weaker than the node fills so the nodes inside still
    # separate from their background. They are styled at all because mermaid's
    # *default* subgraph fill is a yellow that reads as "warning" — a neutral
    # group box has to be asked for.
    "lane": ("#f6f6f4", "#898781"),
    "laneBad": ("#fdefef", "#d03b3b"),
    "laneWarn": ("#fef7e8", "#fab219"),
    "laneGood": ("#eef9ee", "#0ca30c"),
}


def esc(text: object, limit: int = 46) -> str:
    """Make `text` safe inside a double-quoted mermaid label.

    Callers pass *fragments*: deliberate `<br/>` separators are concatenated
    outside this function, so escaping never eats a line break. `#` is replaced
    first, so the `#` it introduces for the others is not escaped twice.
    """
    t = " ".join(str(text).split())
    if len(t) > limit:
        t = t[: limit - 1] + "…"
    for a, b in (("#", "#35;"), ('"', "#quot;"), ("<", "#lt;"), (">", "#gt;")):
        t = t.replace(a, b)
    return t


def classdefs(names: list[str] | tuple[str, ...], indent: str = "    ") -> list[str]:
    """`classDef` lines for the roles a diagram actually used.

    Emitting the whole palette every time is harmless to the render and noise in
    the diff, so callers pass the subset they styled. An unknown name raises
    rather than silently producing an unstyled class, which renders as mermaid's
    default fill and looks like a deliberate choice.
    """
    out = []
    for n in names:
        fill, stroke = PALETTE[n]
        out.append(f"{indent}classDef {n} fill:{fill},stroke:{stroke},"
                   f"stroke-width:2px,color:{INK}")
    return out


# ------------------------------------------------------------------- lint ----
#: Edge operators this repository emits, longest first so the alternation does
#: not match a prefix. Deliberately not the whole mermaid grammar: a linter that
#: claims to parse everything and does not is worse than one with a stated scope.
_OPS = ("-.->", "-.-", "==>", "===", "--x", "--o", "-->", "---", "==")
_ARROW = re.compile("|".join(re.escape(o) for o in _OPS))

#: `-.label.->` puts the label *inside* the operator. This cost five false
#: positives the first time this linter was written against a real diagram.
_DOTTED_LABELLED = re.compile(r"-\.[^.\n]*\.->")
_PIPE_LABEL = re.compile(r"\|[^|\n]*\|")

#: `ID`, or `ID` followed by a label opener. Openers are longest-first for the
#: same reason as the operators.
_ATOM = re.compile(r"^([A-Za-z][A-Za-z0-9_]*)\s*(\(\[|\[\[|\[|\(\(|\(|\{\{|\{|>)?")

_SUBGRAPH = re.compile(r"^\s*subgraph\s+([A-Za-z][A-Za-z0-9_]*)")
_CLASSDEF = re.compile(r"^\s*classDef\s+([A-Za-z][A-Za-z0-9_]*)")
_CLASS_STMT = re.compile(r"^\s*class\s+([A-Za-z0-9_,\s]+?)\s+([A-Za-z][A-Za-z0-9_]*)\s*$")
_INLINE_CLASS = re.compile(r":::([A-Za-z][A-Za-z0-9_]*)")
_QUOTED = re.compile(r'"([^"]*)"')

#: Statement keywords that are not node references.
_KEYWORDS = {"flowchart", "graph", "subgraph", "end", "direction", "classDef",
             "class", "style", "linkStyle", "click", "sequenceDiagram",
             "stateDiagram", "erDiagram", "%%"}


def blocks(markdown: str) -> list[str]:
    """Every ```mermaid fence in a document, without its fence lines."""
    out, buf, inside = [], [], False
    for line in markdown.splitlines():
        if not inside and line.strip().startswith("```mermaid"):
            inside, buf = True, []
            continue
        if inside and line.strip().startswith("```"):
            out.append("\n".join(buf))
            inside = False
            continue
        if inside:
            buf.append(line)
    return out


def lint(block: str) -> list[str]:
    """Problems in one mermaid block, as human sentences. Empty means clean.

    Catches the four failures that are invisible in the source and expensive in
    the render: an edge to a node nobody declared, two nodes sharing an id
    (mermaid merges them and a layer disappears), a class that was used but
    never defined (renders as the default fill, reads as a choice), and a raw
    `<` in a label (swallowed as a tag).
    """
    declared: dict[str, str] = {}     # id -> the label it was declared with
    referenced: set[str] = set()
    defined_classes: set[str] = set()
    used_classes: set[str] = set()
    problems: list[str] = []

    for raw in block.splitlines():
        line = raw.strip()
        if not line or line.startswith("%%"):
            continue

        m = _CLASSDEF.match(raw)
        if m:
            defined_classes.add(m.group(1))
            continue
        m = _SUBGRAPH.match(raw)
        if m:
            declared.setdefault(m.group(1), "")
            continue
        m = _CLASS_STMT.match(raw)
        if m:
            used_classes.add(m.group(2))
            referenced.update(x.strip() for x in m.group(1).split(",") if x.strip())
            continue

        used_classes.update(_INLINE_CLASS.findall(line))

        for label in _QUOTED.findall(line):
            stripped = label.replace("<br/>", "").replace("<br>", "")
            if "<" in stripped or ">" in stripped:
                problems.append(
                    f"raw angle bracket in label {label!r} — htmlLabels is on, so "
                    "it is parsed as a tag and silently dropped; use viz.esc()")

        # Normalise the operators away, then read what is left as atoms.
        stmt = _DOTTED_LABELLED.sub(" --> ", line)
        stmt = _PIPE_LABEL.sub("", stmt)
        parts = [p.strip() for p in _ARROW.split(stmt) if p.strip()]
        if len(parts) == 1 and not _ARROW.search(stmt):
            # A lone statement is only a declaration if it opens a label.
            pass
        for part in parts:
            word = part.split()[0] if part.split() else ""
            if word in _KEYWORDS:
                continue
            m = _ATOM.match(part)
            if not m:
                continue
            node_id, opener = m.group(1), m.group(2)
            if opener:
                label = _QUOTED.search(part)
                text = label.group(1) if label else ""
                if node_id in declared and declared[node_id] and text != declared[node_id]:
                    problems.append(
                        f"node id {node_id!r} declared twice with different labels "
                        f"({declared[node_id]!r} then {text!r}) — mermaid merges "
                        "them and one box vanishes")
                declared[node_id] = text or declared.get(node_id, "")
            else:
                referenced.add(node_id)

    for node_id in sorted(referenced - set(declared)):
        problems.append(f"edge references undeclared node {node_id!r}")
    for cls in sorted(used_classes - defined_classes):
        problems.append(f"class {cls!r} used but no classDef defines it")
    return problems
