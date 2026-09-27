"""A project's architecture blueprint lands with the change it describes.

`pf blueprint build` stamps the page with a fingerprint of what it is built
from; `pf blueprint check` and the commit gate (`blueprint_required`) compare
that stamp with the tree. The first test is the CI half: a pull request whose
committed page is stale against its own inputs fails here, on every runner,
without a warehouse. The rest pin down what counts as an input and how the gate
judges a run.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from conftest import REPO_ROOT
from pf.loops.gate import check_blueprint
from pf.projections import blueprint as bp


def _projects_with_blueprints() -> list[Path]:
    """Every project with a knowledge graph: the page is default-on, spec or not."""
    return sorted(
        p.parents[1]
        for p in (REPO_ROOT / "groups").glob("*/projects/*/kg/graph.json")
        if bp.has_blueprint(p.parents[1])
    )


def test_every_project_has_a_blueprint() -> None:
    """Default-on: a project with a graph and no spec still has a page, so a
    project scaffolded tomorrow is covered without anyone remembering to opt in."""
    projects = _projects_with_blueprints()
    assert projects, "no project has a knowledge graph — nothing to judge"
    assert any(not bp.spec_path(p).is_file() for p in projects), "every project has a spec; defaults are unexercised"


@pytest.mark.parametrize("project_dir", _projects_with_blueprints(), ids=lambda p: p.name)
def test_every_committed_blueprint_is_current(project_dir: Path) -> None:
    group = project_dir.parents[1].name
    result = bp.check(project_dir, group, project_dir.name)
    assert result.state == "current", result.message


def test_the_inputs_are_what_the_page_is_built_from() -> None:
    for rel in (
        "docs/blueprint.yaml",
        "kg/graph.json",
        "mdl/mdl.json",
        "transform/dbt_project.yml",
        "transform/models/marts/mcx/fct_x.sql",
        "transform/macros/m.sql",
        "src/pkg/defs/mcx.py",
        "tools.yaml",
    ):
        assert bp.is_input(rel), rel
    for rel in (
        "docs/mcx.md",
        "transform/models/marts/schema.yml",
        "reporting/pages/index.md",
        "src/pkg/__pycache__/x.py",
        "kg/context_card.md",
    ):
        assert not bp.is_input(rel), rel


def _project(tmp: Path) -> Path:
    d = tmp / "groups" / "g" / "projects" / "p"
    for rel, text in {
        bp.SPEC: "output: docs/blueprint.html\n",
        "kg/graph.json": '{"nodes": [], "edges": []}',
        "mdl/mdl.json": '{"models": []}',
        "transform/dbt_project.yml": "name: p\n",
        "transform/models/a.sql": "select 1 as a\n",
        "docs/notes.md": "notes\n",
    }.items():
        (d / rel).parent.mkdir(parents=True, exist_ok=True)
        (d / rel).write_text(text)
    return d


def _stamp(d: Path) -> None:
    (d / "docs" / "blueprint.html").write_text(
        f'<meta name="pf-blueprint-inputs" content="{bp.fingerprint(d)}">\n<p>page</p>\n'
    )


def test_the_fingerprint_moves_with_an_input_and_only_an_input(tmp_path: Path) -> None:
    d = _project(tmp_path)
    before = bp.fingerprint(d)
    (d / "docs" / "notes.md").write_text("other notes\n")
    (d / "transform" / "target").mkdir(parents=True)
    (d / "transform" / "target" / "x.sql").write_text("select 2\n")
    assert bp.fingerprint(d) == before
    (d / "transform" / "models" / "a.sql").write_text("select 2 as a\n")
    assert bp.fingerprint(d) != before


def test_check_says_missing_then_current_then_stale(tmp_path: Path) -> None:
    d = _project(tmp_path)
    assert bp.check(d, "g", "p").state == "missing"
    _stamp(d)
    assert bp.check(d, "g", "p").state == "current"
    (d / "mdl" / "mdl.json").write_text('{"models": [{"name": "m"}]}')
    stale = bp.check(d, "g", "p")
    assert stale.state == "stale" and "pf blueprint build g p" in stale.message
    assert bp.check(tmp_path, "g", "none").state == "none"


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def test_the_gate_refuses_an_input_change_without_the_rebuilt_page(tmp_path: Path) -> None:
    (tmp_path / "gate.yaml").write_text('blueprint_required:\n  - scope: "groups/*/projects/*/**"\n')
    d = _project(tmp_path)
    _stamp(d)
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "-c", "user.email=t@t", "-c", "user.name=t", "add", "-A")
    _git(tmp_path, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "base")
    model = "groups/g/projects/p/transform/models/a.sql"
    page = "groups/g/projects/p/docs/blueprint.html"

    # Not an input: nothing to judge.
    (d / "docs" / "notes.md").write_text("changed\n")
    assert check_blueprint(["groups/g/projects/p/docs/notes.md"], tmp_path) == []

    # An input changed, the page left behind: stale.
    (d / "transform" / "models" / "a.sql").write_text("select 3 as a\n")
    stale = check_blueprint([model], tmp_path)
    assert [r.rule for r in stale] == ["blueprint_required:g/p"] and "stale" in stale[0].message

    # Rebuilt on disk but not in the run: the commit would lack it.
    _stamp(d)
    unstaged = check_blueprint([model], tmp_path)
    assert len(unstaged) == 1 and "not in this run" in unstaged[0].message

    # Rebuilt and carried: allowed.
    _git(tmp_path, "add", page)
    assert check_blueprint([model, page], tmp_path) == []


def test_a_project_without_a_graph_is_never_judged(tmp_path: Path) -> None:
    (tmp_path / "gate.yaml").write_text('blueprint_required:\n  - scope: "groups/*/projects/*/**"\n')
    d = _project(tmp_path)
    (d / "kg" / "graph.json").unlink()
    assert not bp.has_blueprint(d)
    assert check_blueprint(["groups/g/projects/p/transform/models/a.sql"], tmp_path) == []


def test_a_spec_can_switch_the_page_off(tmp_path: Path) -> None:
    d = _project(tmp_path)
    (d / bp.SPEC).write_text("enabled: false\n")
    assert not bp.has_blueprint(d)
    assert bp.check(d, "g", "p").state == "none"


def test_no_spec_means_the_default_page_not_no_page(tmp_path: Path) -> None:
    d = _project(tmp_path)
    (d / bp.SPEC).unlink()
    assert bp.has_blueprint(d)
    assert bp.output_path(d) == d / bp.DEFAULT_OUTPUT


def test_a_group_tools_change_reaches_every_sister(tmp_path: Path) -> None:
    (tmp_path / "gate.yaml").write_text(
        'blueprint_required:\n  - scope: "groups/*/projects/*/**"\n  - scope: "groups/*/tools.yaml"\n'
    )
    d = _project(tmp_path)
    _stamp(d)
    (tmp_path / "groups" / "g" / "tools.yaml").write_text("version: 1\ntools:\n  wren:\n    enabled: true\n")
    found = check_blueprint(["groups/g/tools.yaml"], tmp_path)
    assert [r.rule for r in found] == ["blueprint_required:g/p"]


def _kg(d: Path) -> None:
    (d / "kg" / "graph.json").write_text(
        '{"nodes": ['
        '{"id": "source:shop", "kind": "Source", "name": "shop", "label": "", "props": {}},'
        '{"id": "table:shop.orders", "kind": "Table", "name": "shop.orders", "label": "", "props": {}},'
        '{"id": "model:stg_orders", "kind": "Model", "name": "stg_orders", "layer": "staging", "label": "", "props": {}}'
        '], "edges": ['
        '{"src": "source:shop", "dst": "table:shop.orders", "kind": "contains", "props": {}},'
        '{"src": "table:shop.orders", "dst": "model:stg_orders", "kind": "feeds", "props": {}}'
        "]}"
    )


def test_the_default_page_follows_the_project_it_describes(tmp_path: Path) -> None:
    """No spec, no warehouse: the page is still written, from the project's own
    sources and tools, and a tool that is off is not drawn."""
    d = _project(tmp_path)
    (d / bp.SPEC).unlink()
    _kg(d)
    page = bp.render(d, "g", "p", {})
    assert f'content="{bp.fingerprint(d)}"' in page
    assert "p Architecture Blueprint" in page and "dlt · shop" in page
    assert "Not traced yet" in page
    assert "wren api" not in page  # wren is not enabled for this project
    (tmp_path / "groups" / "g" / "tools.yaml").write_text("version: 1\ntools:\n  openmetadata:\n    enabled: true\n")
    assert "catalog_sync" in bp.render(d, "g", "p", {})
