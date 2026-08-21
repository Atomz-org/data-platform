"""Tests for the PR architecture chart.

The chart fails in one direction only, and it fails silently: mermaid that does
not parse renders on GitHub as a red error box where the architecture should be,
on a comment nobody re-reads because the tables below it still look fine. Nothing
in CI notices — `pf pr report` exits 0 either way. So the cases below pin the two
things that actually break a diagram: a stray character out of a branch name or
an exposure owner closing a label early, and an edge drawn to a node id that was
never declared.

The visual half (which hue means what) is not tested here — it is a judgement,
and asserting hex codes would only pin the palette to itself.
"""

from __future__ import annotations

import re

import pytest
from pf.pr import MM_CLASSDEF, MM_MAX_PROJECTS, ProjectSlice, PRReport, markdown, mermaid

LABEL = re.compile(r'\["(.*?)"\]')
USED_CLASS = re.compile(r":::(\w+)|^\s*class \w+ (\w+)$", re.M)
DECLARED = re.compile(r"^\s{4,}([A-Za-z]\w*)[\[(]", re.M)


def report(**kw) -> PRReport:
    base = {'number': 1, 'title': "t", 'branch': "b", 'base': "origin/main", 'commit': "c0ffee",
                'generated_at': "now", 'files': ["a.sql"]}
    return PRReport(**{**base, **kw})


def slice_(**kw) -> ProjectSlice:
    base = {'group': "acme", 'project': "acme-us", 'files': ["a.sql"], 'nodes': ["model:stg_a"]}
    return ProjectSlice(**{**base, **kw})


def body(r: PRReport) -> str:
    """The diagram without its fence — what mermaid itself would parse."""
    out = mermaid(r)
    assert out.startswith("```mermaid\n") and out.endswith("\n```")
    return out[len("```mermaid\n"):-len("\n```")]


# ------------------------------------------------------------------ shape ----
@pytest.mark.parametrize("kw, verdict", [
    ({}, "clear"),
    ({"platform_touched": ["platform/src/pf/x.py"]}, "review"),
    ({"gate_denied": ["x: nope"]}, "block"),
    ({"projects": [slice_(severity="breaking")]}, "block"),
])
def test_every_verdict_draws_a_chart(kw, verdict):
    r = report(**kw)
    assert r.verdict == verdict
    assert "flowchart LR" in body(r)


def test_markdown_embeds_exactly_one_chart():
    md = markdown(report(projects=[slice_()]))
    assert md.count("```mermaid") == 1
    # Above the detail tables, and not inside a <details> — a collapsed diagram
    # is one nobody opens.
    assert md.index("```mermaid") < md.index("### Projects touched")


def test_no_projects_still_says_so():
    assert "no project files touched" in body(report(projects=[]))


# --------------------------------------------------------------- escaping ----
def test_hostile_characters_cannot_close_a_label():
    """`"` ends a label, `#` opens an entity, `<` is a tag under htmlLabels.

    The `<` case is the one that bites in practice: exposure owners are written
    `Name <addr@host>`, so it reaches the diagram on any PR touching an exposure.
    """
    r = report(
        number=0, branch='feat/a"b#c<d>',
        projects=[slice_(nodes=['model:x"y', "model:b#c"],
                         owners=["Data Science <ds@jaffle.test>"],
                         impact={"exposures": [{"name": "dash"}]})])
    for label in LABEL.findall(body(r)):
        bare = label.replace("<br/>", "")
        assert '"' not in bare, label
        assert "<" not in bare and ">" not in bare, label
        # Every surviving `#` must open one of the entities we emit.
        for hit in re.finditer(r"#(?!35;|quot;|lt;|gt;)", bare):
            pytest.fail(f"unescaped # at {hit.start()} in {label!r}")


def test_owner_name_survives_escaping():
    r = report(projects=[slice_(owners=["Data Science <ds@jaffle.test>"],
                                impact={"exposures": [{"name": "d"}]})])
    assert "Data Science" in body(r)


# -------------------------------------------------------------- structure ----
def test_no_edge_points_at_an_undeclared_node():
    """A typo'd id renders as an extra empty box, not an error — so assert it."""
    r = report(
        platform_touched=["platform/src/pf/x.py"], gate_denied=["x: nope"],
        vendor=[{"id": "v", "needs_review": True, "paths": []}],
        projects=[slice_(severity="breaking", owners=["o"],
                         conformance_errors=["bad grain"],
                         impact={"models": [{"name": "m"}], "metrics": [{"name": "x"}],
                                 "exposures": [{"name": "e"}]}),
                  slice_(project="acme-eu", impact={"note": "stale"})])
    src = body(r)
    declared = set(DECLARED.findall(src)) | {"PR"}
    referenced = set()
    for line in src.splitlines():
        if "-->" not in line:
            continue
        # Chained edges (`A --> B --> C`) and labelled dotted edges alike.
        referenced |= set(re.findall(r"[A-Za-z]\w*", re.sub(r"\|[^|]*\|", " ", line)))
    assert referenced <= declared, referenced - declared


def test_no_id_is_declared_twice():
    """Two boxes sharing an id do not error — mermaid silently merges them into
    one, so `metrics` would quietly vanish into `models`. Only an id collision
    can cause it, and only counting declarations can see it."""
    r = report(projects=[slice_(severity="breaking", owners=["o"],
                                conformance_errors=["bad grain"],
                                impact={"models": [{"name": "m"}],
                                        "metrics": [{"name": "x"}],
                                        "exposures": [{"name": "e"}],
                                        "note": "stale"})])
    ids = DECLARED.findall(body(r))
    dupes = {i for i in ids if ids.count(i) > 1}
    assert not dupes, dupes


def test_every_class_used_is_defined():
    r = report(projects=[slice_(severity=s) for s in ("safe", "review", "breaking")],
               vendor=[{"id": "v", "needs_review": False, "paths": []}],
               platform_touched=["platform/x.py"])
    src = body(r)
    defined = {name for name, _, _ in MM_CLASSDEF}
    used = {a or b for a, b in USED_CLASS.findall(src)}
    assert used <= defined, used - defined
    assert set(re.findall(r"classDef (\w+)", src)) == defined


def test_project_count_is_capped():
    over = MM_MAX_PROJECTS + 3
    r = report(projects=[slice_(project=f"p{i}") for i in range(over)])
    src = body(r)
    assert f"+{over - MM_MAX_PROJECTS} more project(s)" in src
    assert f"P{MM_MAX_PROJECTS}F" not in src


def test_sisters_are_drawn_inside_their_own_group():
    """Two groups must never share a container — that is the one thing the chart
    is claiming about isolation, and it is the platform's core invariant."""
    r = report(projects=[slice_(group="acme", project="acme-us"),
                         slice_(group="jaffle", project="jaffle-shop")])
    src = body(r)
    assert src.count("subgraph G") == 2
    assert 'subgraph G0["acme"]' in src and 'subgraph G1["jaffle"]' in src
