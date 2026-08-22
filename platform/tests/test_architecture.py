"""Tests for the per-project architecture map.

The map makes one promise that is easy to state and easy to break quietly: it
accounts for **every** feature of the project it describes. A document that
silently omits a feature is worse than no document, because a reader who has
been told it is complete stops looking.

Three of these tests defend that promise from different directions:

  the registry covers the tree   `unmapped` is empty for every real project, so
                                   a directory added by a future capability
                                   fails here on the day it lands
  the registry covers itself     every generated artefact `pf bootstrap`
                                   produces is a feature, so a new bootstrap
                                   step cannot go unreported
  absent is reported             a feature that is not there is a row, not a
                                   silence — the whole reason for the table

The rest defend the two properties that make it usable at all: it renders
without a graph, a warehouse or any built state, and it is byte-stable for a
fixed project so `pf arch --check` measures drift rather than noise.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pf import architecture as arch
from pf import viz

ROOT = Path(__file__).resolve().parents[2]


def _projects() -> list[tuple[str, str]]:
    groups = ROOT / "groups"
    if not groups.exists():
        return []
    return sorted((g.name, p.name)
                  for g in groups.iterdir() if g.is_dir()
                  for p in (g / "projects").iterdir()
                  if (g / "projects").exists() and p.is_dir()
                  and not p.name.startswith("."))


def _bare(tmp_path: Path, group: str = "demo", project: str = "demo-us") -> Path:
    """A project directory with nothing in it. The state at scaffold time."""
    (tmp_path / "groups" / group / "projects" / project).mkdir(parents=True)
    return tmp_path


# --------------------------------------------------------------- coverage ----
@pytest.mark.parametrize(("group", "project"), _projects(),
                         ids=lambda x: x if isinstance(x, str) else "")
def test_no_directory_in_a_real_project_is_unmapped(group: str, project: str) -> None:
    """The anti-omission guard, run against every project that exists.

    A capability that adds `catalog/` to a project and nothing to
    `pf.architecture.FEATURES` fails here. That is the intended failure: the map
    claims to be the inventory, so an unclaimed directory is the map being
    wrong, not the project.
    """
    a = arch.gather(ROOT, group, project)

    assert not a.unmapped, (
        f"{group}/{project} holds {a.unmapped} that no Feature claims — add an "
        "entry to pf.architecture.FEATURES (or to IGNORED if it is build output)")


def test_every_bootstrap_artefact_is_a_feature() -> None:
    """A new bootstrap step must show up in the map.

    Bootstrap is where platform capabilities reach projects, so it is the exact
    seam a new feature arrives through. Steps that write nothing into the
    project — the OWL export and the vendor docs are platform-wide — have
    nothing to report and are named here rather than silently tolerated.
    """
    from pf.scaffold.bootstrap import STEPS

    #: Steps whose output is not a per-project artefact. Keep this shrinking.
    NOT_PER_PROJECT = {"OWL export", "vendor docs", "directories", "group card",
                       "tools", "capabilities", "conformance", "architecture map"}
    covered = {
        "knowledge graph": "graph", "context card": "card", "MDL manifest": "mdl",
        "otop manifest": "otop", "reporting": "reporting",
        "ci workflow": "ci", "dagster code location": "code_location",
        "dbt wiring": "profiles",
    }
    keys = {f.key for f in arch.FEATURES}

    for step in STEPS:
        if step.name in NOT_PER_PROJECT:
            continue
        assert step.name in covered, (
            f"bootstrap step {step.name!r} writes something into a project and no "
            "Feature reports it — add one to pf.architecture.FEATURES")
        assert covered[step.name] in keys


def test_an_absent_feature_is_reported_rather_than_omitted(tmp_path: Path) -> None:
    """The table's whole reason for existing."""
    root = _bare(tmp_path)

    a = arch.gather(root, "demo", "demo-us")
    out = arch.render(a)

    assert a.gaps, "an empty project is all gaps"
    for f in arch.FEATURES:
        assert f.title in out, f"{f.key} vanished from the map"
    assert "## Gaps" in out
    # A gap without a route is a dead end.
    assert "pf evals-gen" in out


def test_every_feature_declares_where_it_comes_from() -> None:
    for f in arch.FEATURES:
        assert f.made_by, f"{f.key}: an absent row has to name its fix"
        assert f.lane in arch.LANES, f"{f.key}: lane {f.lane!r} is not a lane"
        assert f.paths or f.repo_paths, f"{f.key}: nothing to detect it by"


def test_feature_keys_are_unique() -> None:
    keys = [f.key for f in arch.FEATURES]
    assert len(keys) == len(set(keys))


# --------------------------------------------------------------- rendering ---
def test_it_renders_for_a_project_with_nothing_in_it(tmp_path: Path) -> None:
    """Bootstrap runs this on a project with no graph, no dbt and no warehouse."""
    root = _bare(tmp_path)

    out = arch.render(arch.gather(root, "demo", "demo-us"))

    assert "demo-us — architecture" in out
    assert "run `pf seed`" in out, "say what to do, not just that there is nothing"
    assert not arch.lint_doc(out)


@pytest.mark.parametrize(("group", "project"), _projects(),
                         ids=lambda x: x if isinstance(x, str) else "")
def test_every_diagram_parses(group: str, project: str) -> None:
    """A malformed diagram renders as a red box while the job still exits 0.

    Which means nothing fails, and the map is silently broken in the one place
    it was supposed to be worth more than prose.
    """
    problems = arch.lint_doc(arch.render(arch.gather(ROOT, group, project)))

    assert not problems, f"{group}/{project}: " + "; ".join(problems)


@pytest.mark.parametrize(("group", "project"), _projects(),
                         ids=lambda x: x if isinstance(x, str) else "")
def test_the_map_stays_inside_its_budget(group: str, project: str) -> None:
    """jaffle-shop has 996 marts. Every section is capped for that reason."""
    from pf.kg.card import estimate_tokens

    n = estimate_tokens(arch.render(arch.gather(ROOT, group, project)))

    assert n <= arch.ARCHITECTURE_BUDGET, (
        f"{group}/{project}: ~{n} tokens — cap a section rather than the budget")


def test_render_is_byte_stable_for_a_fixed_project() -> None:
    """`pf arch --check` is drift detection, so instability is a false alarm.

    Dict iteration, `Path.glob` order and set ordering have all produced maps
    that differed between two runs against an unchanged project.
    """
    group, project = _projects()[0]

    first = arch.render(arch.gather(ROOT, group, project))
    second = arch.render(arch.gather(ROOT, group, project))

    assert first == second


def test_the_map_does_not_report_itself_as_missing(tmp_path: Path) -> None:
    """It is written by the render that describes it.

    Detected like any other feature it is absent in the file it produces and
    present the next time round, so the document never matches what the project
    would generate and `pf arch --check` reports drift forever.
    """
    root = _bare(tmp_path)

    path, _ = arch.write(root, "demo", "demo-us")

    assert path.exists()
    assert arch.drift(root, "demo", "demo-us").ok, "written and immediately stale"


def test_a_graph_with_no_tables_is_not_papered_over_by_a_file_count(
        tmp_path: Path) -> None:
    """A `data/*.duckdb` file is not evidence that anything was loaded into it.

    A roll-up reported "raw tables: 1" on the strength of an empty warehouse
    file while its graph held no tables at all.
    """
    from pf.kg.store import Node, open_graph

    root = _bare(tmp_path)
    d = root / "groups" / "demo" / "projects" / "demo-us"
    (d / "data").mkdir()
    (d / "data" / "demo_us.duckdb").write_bytes(b"")

    # No graph at all: the file is the only evidence there is, so it counts.
    assert arch.gather(root, "demo", "demo-us").n("raw_tables") == 1

    # A graph holding no Table is positive evidence that nothing was loaded, and
    # it outranks the file. Falling back on a missing *kind* rather than a
    # missing *graph* is what produced the wrong answer.
    with open_graph(d / "kg" / "graph.duckdb") as g:
        g.add_nodes([Node(id="model:x", kind="Model", name="x")])

    assert arch.gather(root, "demo", "demo-us").n("raw_tables") == 0


# ----------------------------------------------------------------- drift -----
def test_drift_reports_a_missing_map_separately_from_a_stale_one(
        tmp_path: Path) -> None:
    """They have different fixes, so they cannot be the same message."""
    root = _bare(tmp_path)

    d = arch.drift(root, "demo", "demo-us")
    assert d.missing and not d.ok
    assert "pf arch" in str(d)

    arch.write(root, "demo", "demo-us")
    (root / "groups" / "demo" / "projects" / "demo-us" / arch.DOC_REL).write_text("x")

    d = arch.drift(root, "demo", "demo-us")
    assert d.stale and not d.missing


def test_the_summary_is_json_serialisable() -> None:
    """`pf arch --json` and the control plane both consume it."""
    group, project = _projects()[0]

    payload = json.loads(arch.as_json(arch.gather(ROOT, group, project)))

    assert payload["project"] == project
    assert set(payload["features"]) == {f.key for f in arch.FEATURES}


# ------------------------------------------------------------- isolation -----
def test_gathering_reads_nothing_outside_its_own_project(monkeypatch) -> None:
    """The platform's first rule, enforced rather than intended.

    An architecture read from a sister is not slightly wrong, it is wrong in the
    way that matters: business logic does not transfer between entities. Only
    two things outside the project directory are legitimate — the repository
    artefacts that are *about* it — and a roll-up's sister directory listing,
    which yields names and opens no file.
    """
    opened: list[str] = []
    real = Path.read_text

    def spy(self, *a, **kw):
        opened.append(str(self))
        return real(self, *a, **kw)

    monkeypatch.setattr(Path, "read_text", spy)
    arch.gather(ROOT, "acme", "acme-us")

    # Only reads under `groups/` are judged. `platform/`, `vendor/`, repo config
    # and the interpreter's own package metadata are shared by construction, and
    # listing them as exceptions would make this pass for the wrong reason.
    for p in opened:
        try:
            parts = Path(p).relative_to(ROOT).parts
        except ValueError:
            continue
        if parts[:1] != ("groups",):
            continue
        assert parts[1] == "acme", f"read another group: {'/'.join(parts)}"
        if len(parts) > 3 and parts[2] == "projects":
            assert parts[3] == "acme-us", f"read a sister: {'/'.join(parts)}"


# ------------------------------------------------------------------- viz -----
def test_the_linter_catches_what_it_claims_to() -> None:
    """It is the only thing standing between a bad diagram and a red box."""
    assert viz.lint('flowchart LR\n    A["ok"] --> B["ok"]\n'
                    "    classDef x fill:#fff,stroke:#000") == []

    assert any("undeclared" in p for p in
               viz.lint('flowchart LR\n    A["ok"] --> B'))
    assert any("declared twice" in p for p in
               viz.lint('flowchart LR\n    A["one"]\n    A["two"]'))
    assert any("classDef" in p for p in
               viz.lint('flowchart LR\n    A["ok"]:::ghost'))
    assert any("angle bracket" in p for p in
               viz.lint('flowchart LR\n    A["owner <me@x.test>"]'))


def test_the_linter_understands_a_labelled_dotted_edge() -> None:
    """`-.label.->` puts the label inside the operator, and a linter that cannot
    read it reports every arrow in the map as a broken node."""
    assert viz.lint('flowchart LR\n    A["a"] -.governs.-> B["b"]') == []


def test_classdefs_refuses_a_colour_that_is_not_in_the_palette() -> None:
    """Loudly, rather than emitting an unstyled class that renders as a choice."""
    with pytest.raises(KeyError):
        viz.classdefs(["chartreuse"])


def test_the_pr_report_and_the_map_share_one_palette() -> None:
    """Two copies of a palette agree until one of them is edited."""
    from pf.pr import MM_CLASSDEF, MM_ROLES

    for name, role in MM_ROLES.items():
        assert role in viz.PALETTE, f"{name} maps to a role no palette defines"
    for _, fill, stroke in MM_CLASSDEF:
        assert (fill, stroke) in set(viz.PALETTE.values())
