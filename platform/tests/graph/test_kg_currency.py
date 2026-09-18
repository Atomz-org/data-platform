"""Tests for the graph currency check and the bulk graph commands.

The graph is a build artefact with no clock. One built before a model landed
answers every query confidently and wrongly, and nothing else in the repo
notices — it simply holds fewer nodes than the project has models. Every other
guarantee is downstream of that: the impact gate computes a blast radius from
the graph, and an agent reads its context card.

The check has to be warehouse-independent to be worth having. A CI runner has a
checkout and no warehouse, so a check that compared *columns* — backfilled from
`information_schema` — would be red on every pull request forever, and a
permanently red check is one nobody reads.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pf.kg.build import graph_drift


def _manifest(pdir: Path, models: list[str], exposures: list[str] | None = None) -> None:
    nodes = {
        f"model.demo.{m}": {"resource_type": "model", "name": m, "path": f"marts/{m}.sql"}
        for m in models
    }
    exps = {f"exposure.demo.{e}": {"name": e, "type": "dashboard"} for e in exposures or []}
    target = pdir / "transform" / "target"
    target.mkdir(parents=True, exist_ok=True)
    (target / "manifest.json").write_text(
        json.dumps({"nodes": nodes, "exposures": exps, "parent_map": {}, "child_map": {}}))


def _semantic(pdir: Path, metrics: list[str]) -> None:
    target = pdir / "transform" / "target"
    target.mkdir(parents=True, exist_ok=True)
    (target / "semantic_manifest.json").write_text(
        json.dumps({"metrics": [{"name": m, "type": "simple"} for m in metrics],
                    "semantic_models": []}))


def _graph_json(pdir: Path, nodes: list[tuple[str, str]]) -> None:
    kg = pdir / "kg"
    kg.mkdir(parents=True, exist_ok=True)
    (kg / "graph.json").write_text(json.dumps({
        "nodes": [{"id": f"{k.lower()}:{n}", "kind": k, "name": n,
                   "layer": "", "label": "", "props": {}} for k, n in nodes],
        "edges": [],
    }))


# ------------------------------------------------------------- the check ----
def test_a_current_graph_reports_no_drift(tmp_path: Path) -> None:
    _manifest(tmp_path, ["fct_payments", "dim_customers"])
    _graph_json(tmp_path, [("Model", "fct_payments"), ("Model", "dim_customers")])

    d = graph_drift(tmp_path, "demo/demo-us")

    assert d.exercised
    assert d.total == 0
    assert "current" in d.render()


def test_a_model_added_after_the_last_build_is_caught(tmp_path: Path) -> None:
    """The failure this exists for: the graph predates a model in the project."""
    _manifest(tmp_path, ["fct_payments", "fct_revenue"])
    _graph_json(tmp_path, [("Model", "fct_payments")])

    d = graph_drift(tmp_path, "demo/demo-us")

    assert d.exercised
    assert d.models == ["fct_revenue"]
    assert d.total == 1
    assert "fct_revenue" in d.render()
    assert "pf kg build" in d.render(), "a failure must say how to fix it"


def test_metrics_and_exposures_drift_too(tmp_path: Path) -> None:
    _manifest(tmp_path, ["fct_payments"], exposures=["exec_dashboard"])
    _semantic(tmp_path, ["revenue", "aov"])
    _graph_json(tmp_path, [("Model", "fct_payments"), ("Metric", "revenue")])

    d = graph_drift(tmp_path, "demo/demo-us")

    assert d.metrics == ["aov"]
    assert d.exposures == ["exec_dashboard"]
    assert d.total == 2


def test_columns_are_not_compared(tmp_path: Path) -> None:
    """Columns are backfilled from the warehouse, which CI does not have.

    Comparing them would make this check red on every pull request forever, and
    a permanently red check is one nobody reads. A graph holding no columns at
    all is still *current* by this measure.
    """
    _manifest(tmp_path, ["fct_payments"])
    _graph_json(tmp_path, [("Model", "fct_payments")])  # no Column nodes at all

    assert graph_drift(tmp_path, "demo/demo-us").total == 0


# ------------------------------------------------------- cannot be judged ---
def test_no_manifest_is_not_exercised_rather_than_clean(tmp_path: Path) -> None:
    """A green tick meaning "found nothing" is worse than no check."""
    _graph_json(tmp_path, [("Model", "fct_payments")])

    d = graph_drift(tmp_path, "demo/demo-us")

    assert not d.exercised
    assert d.total == 0
    assert "not exercised" in d.render()


def test_a_graph_that_was_never_built_is_not_exercised(tmp_path: Path) -> None:
    _manifest(tmp_path, ["fct_payments"])

    d = graph_drift(tmp_path, "demo/demo-us")

    assert not d.exercised
    assert "never been built" in d.reason


# ------------------------------------------------------------ the reach -----
def test_the_ci_job_is_carried_by_a_default_capability() -> None:
    """The job must arrive without anyone remembering to ask for it.

    This is the whole reason it is a capability rather than a workflow file: an
    opt-in check reaches the projects whose author remembered the flag, which is
    how seven graphs go stale while the eighth is gated.
    """
    from pf.capabilities import CAPABILITIES, defaults

    owners = [c for c in CAPABILITIES.values() if "kg-current" in c.ci_jobs]
    assert owners, "no capability contributes the kg-current job"
    assert all(c.name in defaults() for c in owners), \
        "the graph currency check must be default-enabled"


def test_the_ci_job_parameterises_group_and_project() -> None:
    """A job that hardcoded a project would gate the wrong graph everywhere else."""
    from pf.capabilities import KG_CURRENT_JOB

    assert "{{group}}" in KG_CURRENT_JOB and "{{project}}" in KG_CURRENT_JOB
    assert "--strict" in KG_CURRENT_JOB, \
        "without --strict a runner with no manifest passes vacuously"


def test_every_capability_job_renders_without_leftovers() -> None:
    """No `{{placeholder}}` may survive into a generated workflow.

    GitHub's own expressions are `${{ ... }}`, so the test has to distinguish
    them from pf's `{{name}}` rather than searching for `{{`.
    """
    import re

    from pf.capabilities import CAPABILITIES
    from pf.scaffold.ci import render_project_workflow

    jobs: dict[str, str] = {}
    for cap in CAPABILITIES.values():
        jobs.update(cap.ci_jobs)
    rendered = render_project_workflow("demo", "demo-us", jobs)

    leftover = re.findall(r"(?<!\$)\{\{\s*\w+\s*\}\}", rendered)
    assert not leftover, f"unsubstituted placeholders: {set(leftover)}"
    assert "pf kg check demo demo-us" in rendered


# ------------------------------------------------------------ bulk scope ----
@pytest.mark.parametrize("group,project,expected", [
    ("", "", {"a/one", "a/two", "b/three"}),   # nothing  -> every project
    ("a", "", {"a/one", "a/two"}),             # a group  -> its projects
    ("a", "one", {"a/one"}),                   # both     -> one project
])
def test_targets_widens_from_nothing_to_one(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        group: str, project: str, expected: set[str]) -> None:
    """`pf kg build` must be runnable at every scope a change happens at."""
    from pf import cli

    (tmp_path / "platform").mkdir()
    for g, p in (("a", "one"), ("a", "two"), ("b", "three")):
        (tmp_path / "groups" / g / "projects" / p).mkdir(parents=True)
    monkeypatch.chdir(tmp_path)

    got = {f"{g}/{p}" for g, p, _ in cli._targets(group, project)}

    assert got == expected


def test_a_project_without_its_group_is_refused(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`pf kg build "" acme-us` is ambiguous: two groups may hold that name."""
    import typer
    from pf import cli

    (tmp_path / "platform").mkdir()
    (tmp_path / "groups" / "a" / "projects" / "one").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)

    with pytest.raises(typer.Exit):
        cli._targets("", "one")
