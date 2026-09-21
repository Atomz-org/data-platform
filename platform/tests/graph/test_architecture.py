"""Per-project architecture map.

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
from conftest import REPO_ROOT
from pf import architecture as arch
from pf import viz

ROOT = REPO_ROOT


def _projects() -> list[tuple[str, str]]:
    groups = ROOT / "groups"
    if not groups.exists():
        return []
    return sorted(
        (g.name, p.name)
        for g in groups.iterdir()
        if g.is_dir()
        for p in (g / "projects").iterdir()
        if (g / "projects").exists() and p.is_dir() and not p.name.startswith(".")
    )


def _bare(tmp_path: Path, group: str = "demo", project: str = "demo-us") -> Path:
    """A project directory with nothing in it. The state at scaffold time."""
    (tmp_path / "groups" / group / "projects" / project).mkdir(parents=True)
    return tmp_path


# --------------------------------------------------------------- coverage ----
@pytest.mark.parametrize(("group", "project"), _projects(), ids=lambda x: x if isinstance(x, str) else "")
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
        "entry to pf.architecture.FEATURES (or to IGNORED if it is build output)"
    )


def test_every_bootstrap_artefact_is_a_feature() -> None:
    """A new bootstrap step must show up in the map.

    Bootstrap is where platform capabilities reach projects, so it is the exact
    seam a new feature arrives through. Steps that write nothing into the
    project — the OWL export and the vendor docs are platform-wide — have
    nothing to report and are named here rather than silently tolerated.
    """
    from pf.scaffold.bootstrap import STEPS

    #: Steps whose output is not a per-project artefact. Keep this shrinking.
    NOT_PER_PROJECT = {
        "OWL export",
        "vendor docs",
        "directories",
        "group card",
        "group air.yaml",
        "tools",
        "capabilities",
        "conformance",
        "architecture map",
        "capability policies",
        "notify channel",
        "pre-commit gate",
        "group manifest",
        "group plugin + loops",
        "platform CI",
    }
    covered = {
        "knowledge graph": "graph",
        "context card": "card",
        "MDL manifest": "mdl",
        "otop manifest": "otop",
        "reporting": "reporting",
        "ci workflow": "ci",
        "dagster code location": "code_location",
        "dbt wiring": "profiles",
        "claude settings": "settings",
        "project atlas": "atlas",
        "dev serving": "docs",
        # Writes `.memory/notes/README.md` — the convention's own explanation,
        # so the directory exists in git. The notes an agent writes there are
        # the `memory` feature; the README is what makes the feature visible.
        "memory notes": "memory",
    }
    keys = {f.key for f in arch.features()}

    for step in STEPS:
        if step.name in NOT_PER_PROJECT:
            continue
        assert step.name in covered, (
            f"bootstrap step {step.name!r} writes something into a project and no "
            "Feature reports it — add one to pf.architecture.CORE"
        )
        assert covered[step.name] in keys


# ------------------------------------------------------------ pluggability ---
def test_a_third_party_tool_claims_its_own_territory(monkeypatch, tmp_path: Path) -> None:
    """The reason the registry is composed rather than listed.

    A tool arrives by installing a package with a `pf.tools` entry point, and
    nothing in this repository changes when one does. So a tool that writes
    `elementary/` into a project has to be able to account for that directory
    itself — otherwise every project reports an unmapped entry and
    `pf arch --check` fails, fixable only by patching platform code.
    """
    from pf.features import Feature
    from pf.tools.spec import Tool

    elementary = Tool(
        name="elementary",
        title="Elementary",
        summary="Anomaly monitors on dbt.",
        features=(
            Feature(
                "elementary",
                "anomaly monitors",
                "operate",
                "statistical monitors over dbt test results",
                ("elementary/**",),
                optional=True,
                made_by="pf tool enable elementary",
                source="tool:elementary",
            ),
        ),
    )
    monkeypatch.setattr(arch, "_installed_tools", lambda: [elementary])

    root = _bare(tmp_path)
    d = root / "groups" / "demo" / "projects" / "demo-us"
    (d / "elementary").mkdir()
    (d / "elementary" / "monitors.yml").write_text("monitors: []\n")

    a = arch.gather(root, "demo", "demo-us")

    assert not a.unmapped, "an installed tool must account for what it writes"
    assert a.by_key("elementary").present
    assert "anomaly monitors" in arch.render(a)


def test_a_tool_that_declares_nothing_still_claims_what_it_writes(monkeypatch, tmp_path: Path) -> None:
    """Declaring a Feature is the refinement, not the price of entry.

    A tool already says where its artefacts go, for `pf tool doctor`. Making it
    repeat that as a Feature would be the kind of duplicated declaration this
    platform keeps removing, so the derivation reads what is already there.
    """
    from pf.tools.spec import DbtBinding, Tool

    mc = Tool(
        name="montecarlo",
        title="Monte Carlo",
        summary="Freshness monitors.",
        dbt=DbtBinding(artefacts=("montecarlo/state.json",)),
    )
    monkeypatch.setattr(arch, "_installed_tools", lambda: [mc])

    root = _bare(tmp_path)
    d = root / "groups" / "demo" / "projects" / "demo-us"
    (d / "montecarlo").mkdir()
    (d / "montecarlo" / "state.json").write_text("{}")

    a = arch.gather(root, "demo", "demo-us")

    assert not a.unmapped
    derived = a.by_key("tool_montecarlo")
    assert derived.present, "the derivation did not read dbt.artefacts"
    assert derived.feature.source == "tool:montecarlo"
    assert derived.feature.lane in arch.LANES


def test_a_contribution_never_overwrites_a_platform_feature(monkeypatch) -> None:
    """`CORE` is the authority on the features the platform itself provides.

    A tool shipping a `Feature(key="graph", ...)` must not be able to redefine
    what the knowledge graph is in every project's map.
    """
    from pf.features import Feature
    from pf.tools.spec import Tool

    hostile = Tool(
        name="x",
        title="X",
        summary="s",
        features=(Feature("graph", "not the graph", "operate", "hijacked", ("elsewhere/**",), made_by="nothing"),),
    )
    monkeypatch.setattr(arch, "_installed_tools", lambda: [hostile])

    graph = next(f for f in arch.features() if f.key == "graph")

    assert graph.source == "platform"
    assert graph.title == "knowledge graph"


def test_capabilities_are_named_even_when_they_earn_no_row() -> None:
    """Nine capabilities writing one page each would be nine identical rows.

    They are summarised on their own line instead — but a capability that is
    present must still be visible somewhere, or the map is silent about why a
    project has a `reporting/` directory at all.
    """
    a = arch.gather(ROOT, "acme", "acme-us")

    assert a.caps, "a scaffolded project has capabilities"
    out = arch.render(a)
    for name in a.caps:
        assert f"`{name}`" in out


def test_an_absent_feature_is_reported_rather_than_omitted(tmp_path: Path) -> None:
    """The table's whole reason for existing."""
    root = _bare(tmp_path)

    a = arch.gather(root, "demo", "demo-us")
    out = arch.render(a)

    assert a.gaps, "an empty project is all gaps"
    for f in arch.features():
        assert f.title in out, f"{f.key} vanished from the map"
    assert "## Gaps" in out
    # A gap without a route is a dead end.
    assert "pf evals-gen" in out


def test_every_feature_declares_where_it_comes_from() -> None:
    for f in arch.features():
        assert f.made_by, f"{f.key}: an absent row has to name its fix"
        assert f.lane in arch.LANES, f"{f.key}: lane {f.lane!r} is not a lane"
        assert f.paths or f.repo_paths, f"{f.key}: nothing to detect it by"


def test_feature_keys_are_unique() -> None:
    keys = [f.key for f in arch.features()]
    assert len(keys) == len(set(keys))


# --------------------------------------------------------------- rendering ---
def test_it_renders_for_a_project_with_nothing_in_it(tmp_path: Path) -> None:
    """Bootstrap runs this on a project with no graph, no dbt and no warehouse."""
    root = _bare(tmp_path)

    out = arch.render(arch.gather(root, "demo", "demo-us"))

    assert "demo-us — architecture" in out
    assert "run `pf seed`" in out, "say what to do, not just that there is nothing"
    assert not arch.lint_doc(out)


@pytest.mark.parametrize(("group", "project"), _projects(), ids=lambda x: x if isinstance(x, str) else "")
def test_every_diagram_parses(group: str, project: str) -> None:
    """A malformed diagram renders as a red box while the job still exits 0.

    Which means nothing fails, and the map is silently broken in the one place
    it was supposed to be worth more than prose.
    """
    problems = arch.lint_doc(arch.render(arch.gather(ROOT, group, project)))

    assert not problems, f"{group}/{project}: " + "; ".join(problems)


@pytest.mark.parametrize(("group", "project"), _projects(), ids=lambda x: x if isinstance(x, str) else "")
def test_the_map_stays_inside_its_budget(group: str, project: str) -> None:
    """jaffle-shop has 996 marts. Every section is capped for that reason."""
    from pf.kg.card import estimate_tokens

    n = estimate_tokens(arch.render(arch.gather(ROOT, group, project)))

    assert n <= arch.ARCHITECTURE_BUDGET, f"{group}/{project}: ~{n} tokens — cap a section rather than the budget"


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


def test_a_graph_with_no_tables_is_not_papered_over_by_a_file_count(tmp_path: Path) -> None:
    """A `data/*.duckdb` file is not evidence that anything was loaded into it.

    A roll-up reported "raw tables: 1" on the strength of an empty warehouse
    file while its graph held no tables at all.

    The file used to count when there was no graph to contradict it, which is
    the same claim in a weaker position: `pf seed` writes that file and CI never
    does, so the fallback made the rendered map differ between a developer's
    checkout and a runner. `Feature.build_output` removes it, and the row now
    says the same thing in both places.
    """
    from pf.kg.store import Node, open_graph

    root = _bare(tmp_path)
    d = root / "groups" / "demo" / "projects" / "demo-us"

    # The same project with and without the local warehouse file. Two renders,
    # one answer: that is the whole point of the flag.
    without = arch.gather(root, "demo", "demo-us").n("raw_tables")
    (d / "data").mkdir()
    (d / "data" / "demo_us.duckdb").write_bytes(b"")
    assert arch.gather(root, "demo", "demo-us").n("raw_tables") == without == 0

    # A graph holding no Table is positive evidence that nothing was loaded, and
    # it outranks the file. Falling back on a missing *kind* rather than a
    # missing *graph* is what produced the wrong answer.
    with open_graph(d / "kg" / "graph.duckdb") as g:
        g.add_nodes([Node(id="model:x", kind="Model", name="x")])

    assert arch.gather(root, "demo", "demo-us").n("raw_tables") == 0


def test_build_output_keeps_the_count_and_drops_only_the_local_filename(tmp_path: Path) -> None:
    """Ignoring the disk must not cost the row its number.

    The tables are nodes in the graph whether or not the DuckDB file is on this
    machine, and that count is what the row is for — dropping it too would have
    traded a map that differs by machine for one that says nothing. Only the
    printed location changes: the declared pattern, which belongs to the
    project, instead of the filename, which belongs to whoever built it.
    """
    from pf.kg.store import Node, open_graph

    root = _bare(tmp_path)
    d = root / "groups" / "demo" / "projects" / "demo-us"
    (d / "data").mkdir()
    (d / "data" / "demo_us.duckdb").write_bytes(b"")
    with open_graph(d / "kg" / "graph.duckdb") as g:
        g.add_nodes([Node(id="table:orders", kind="Table", name="orders")])

    found = arch.gather(root, "demo", "demo-us").by_key("raw_tables")
    assert found.count == 1
    assert found.where == "data/*.duckdb"


# ----------------------------------------------------------------- drift -----
def test_a_stale_map_says_what_differs(tmp_path: Path) -> None:
    """ "The project changed since it was written" is true of every stale map.

    Which is to say it identifies nothing. The check runs on a runner, and when
    the render disagrees there because of the runner's own environment, the
    failing job is the only place the difference exists — reproducing it
    locally is precisely what does not work. So the drift carries the diff.
    """
    root = _bare(tmp_path)
    arch.write(root, "demo", "demo-us")
    out = root / "groups" / "demo" / "projects" / "demo-us" / arch.DOC_REL
    out.write_text(out.read_text().replace("# demo-us", "# somebody-else", 1))

    d = arch.drift(root, "demo", "demo-us")
    assert d.stale
    assert "somebody-else" in d.diff and "somebody-else" in str(d)
    assert "--- committed" in d.diff and "+++ would render" in d.diff


def test_drift_reports_a_missing_map_separately_from_a_stale_one(tmp_path: Path) -> None:
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
    assert set(payload["features"]) == {f.key for f in arch.features()}


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
    assert viz.lint('flowchart LR\n    A["ok"] --> B["ok"]\n    classDef x fill:#fff,stroke:#000') == []

    assert any("undeclared" in p for p in viz.lint('flowchart LR\n    A["ok"] --> B'))
    assert any("declared twice" in p for p in viz.lint('flowchart LR\n    A["one"]\n    A["two"]'))
    assert any("classDef" in p for p in viz.lint('flowchart LR\n    A["ok"]:::ghost'))
    assert any("angle bracket" in p for p in viz.lint('flowchart LR\n    A["owner <me@x.test>"]'))


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


@pytest.mark.parametrize(
    ("args", "reaches"),
    [
        (["acme", "acme-eu", "--help"], "[group] [project]"),  # every project's CI job
        (["--all", "--help"], "[group] [project]"),
        (["build", "--help"], "docs/ARCHITECTURE.md"),  # platform-tests.yml
        (["check", "--help"], "committed map"),
    ],
)
def test_both_maps_answer_to_pf_arch(args: list[str], reaches: str) -> None:
    """`pf arch <group> <project>` and `pf arch build|check` share one name.

    Registered as a command and as a group, the group shadowed the command
    without a word, and every project's CI `architecture` job failed on
    "No such command 'acme'". Bootstrap never noticed: it calls the map
    directly, not through the CLI.
    """
    from pf.cli import app
    from typer.testing import CliRunner

    res = CliRunner().invoke(app, ["arch", *args])
    assert res.exit_code == 0, res.output
    assert reaches in " ".join(res.output.split())


# ------------------------------------------------- the runner's view ----------
def _repo(tmp_path: Path) -> Path:
    """A project inside a git repository, the way a runner sees one."""
    import subprocess

    root = _bare(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True)
    return root


def test_an_untracked_file_does_not_count_inside_a_repository(tmp_path: Path) -> None:
    """The map describes the repository, not this machine.

    Three projects failed their architecture gate because a developer's checkout
    held a `docs/quack.md` nobody had added: the local render counted eight
    docs, the runner's seven, and the committed map could satisfy only one of
    them. A staged file counts — the render after `git add` is the one CI sees.
    """
    import subprocess

    root = _repo(tmp_path)
    d = root / "groups" / "demo" / "projects" / "demo-us"
    (d / "docs").mkdir()
    (d / "docs" / "tracked.md").write_text("# a\n")
    (d / "docs" / "staged.md").write_text("# b\n")
    (d / "docs" / "stray.md").write_text("# c\n")
    subprocess.run(["git", "add", "docs/tracked.md"], cwd=d, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "one"], cwd=d, check=True)
    subprocess.run(["git", "add", "docs/staged.md"], cwd=d, check=True)

    assert arch.gather(root, "demo", "demo-us").n("docs") == 2


def test_outside_a_repository_the_filesystem_still_counts(tmp_path: Path) -> None:
    root = _bare(tmp_path)
    d = root / "groups" / "demo" / "projects" / "demo-us"
    (d / "docs").mkdir()
    (d / "docs" / "a.md").write_text("# a\n")
    assert arch.gather(root, "demo", "demo-us").n("docs") == 1


def test_a_regenerated_artefact_is_a_row_of_its_own_not_a_gap(tmp_path: Path) -> None:
    """`kg/context_card.md` and `platform/workspace.yaml` are gitignored and
    rewritten wherever the project runs. Read from disk they were present on
    the developer's machine and a gap on the runner, and the committed map
    could never satisfy both. Now they are neither: a `⟳` row that says who
    regenerates them.
    """
    root = _bare(tmp_path)
    d = root / "groups" / "demo" / "projects" / "demo-us"
    (d / "kg").mkdir()
    (d / "kg" / "context_card.md").write_text("## card\n")  # present here …
    a = arch.gather(root, "demo", "demo-us")
    card, registration = a.by_key("card"), a.by_key("code_location")
    assert card.state == "generated" and registration.state == "generated"
    assert card not in a.gaps and registration not in a.gaps
    text = arch.render(a)
    assert "| context card | ⟳ |" in text
    assert "regenerated by `pf kg card`, not tracked" in text
    # … and the render is the same when it is absent, which is the point.
    (d / "kg" / "context_card.md").unlink()
    assert arch.render(arch.gather(root, "demo", "demo-us")) == text
