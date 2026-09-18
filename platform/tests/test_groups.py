"""The group as an object, and what leaving costs.

Every failure here is one a human finds out about late: a family that passes
every gate by being empty, a lifecycle that moved somewhere it should not have,
a strict rule applied to a tenant still being built, or an offboarding plan that
looks clean because nothing recorded what the tenant owned.
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import pytest
import yaml
from pf import groups, offboard


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "data_platform" / "data-platform"
    (root / "platform").mkdir(parents=True)
    (root / "groups").mkdir()
    return root


def make_group(repo: Path, name: str, *, lifecycle: str = "provisioned",
               projects: tuple[str, ...] = (), annotated: bool = True,
               domain: str = "commodities", contact: str = "someone@example.com",
               resources: dict | None = None, template: int | None = None) -> Path:
    """A group as bootstrap would leave it, with the knobs each test needs."""
    gdir = repo / "groups" / name
    (gdir / "ontology").mkdir(parents=True)
    (gdir / "ontology" / "instance.yaml").write_text(
        yaml.safe_dump({"group": name, "domain": domain, "classes": ["Product"]}))
    (gdir / "CLAUDE.md").write_text(f"# {name}\n\n- a real business rule\n")
    (gdir / "loops.yaml").write_text("version: 1\nloops: {}\n")
    (gdir / ".claude" / ".claude-plugin").mkdir(parents=True)
    (gdir / ".claude" / ".claude-plugin" / "plugin.json").write_text("{}")
    (gdir / ".claude" / "skills").mkdir(parents=True)
    (gdir / ".claude" / "skills" / "a-skill" / "SKILL.md").parent.mkdir(parents=True)
    (gdir / ".claude" / "skills" / "a-skill" / "SKILL.md").write_text("# skill\n")
    (gdir / "evals").mkdir()
    (gdir / "evals" / "cases.yaml").write_text("cases: []\n")
    (gdir / "kg").mkdir()
    (gdir / "kg" / "group_card.md").write_text("# card\n")
    for p in projects:
        pdir = gdir / "projects" / p
        (pdir / "contracts").mkdir(parents=True)
        if annotated:
            (pdir / "contracts" / "annotations.yaml").write_text("models: {}\n")
    groups.save(groups.Manifest(
        group=name, path=groups.manifest_path(repo, name), domain=domain,
        lifecycle=lifecycle,
        template_version=groups.TEMPLATE_VERSION if template is None else template,
        owner=groups.Owner(team="data", contact=contact),
        data=groups.DataPolicy(residency="local", retention_days=3650,
                               erasure_sla_days=30),
        resources=resources or {}))
    return gdir


# --- the manifest ------------------------------------------------------------


def test_a_manifest_survives_a_round_trip(repo: Path) -> None:
    make_group(repo, "commodity", projects=("commodity-india",))

    m = groups.load(repo, "commodity")

    assert m.group == "commodity" and m.domain == "commodities"
    assert m.owner.contact == "someone@example.com"
    assert m.data.retention_days == 3650 and m.data.erasure_sla_days == 30
    assert not m.behind_template


def test_a_manifest_that_names_a_different_group_is_refused(repo: Path) -> None:
    """The directory is the identity every other part of the platform uses; a
    manifest that disagrees would make a lookup depend on which one was read."""
    make_group(repo, "commodity")
    path = groups.manifest_path(repo, "commodity")
    path.write_text(path.read_text().replace("group: commodity", "group: globex"))

    with pytest.raises(groups.GroupError, match="says group"):
        groups.load(repo, "commodity")


@pytest.mark.parametrize("key,value,message", [
    ("lifecycle", "retired", "not one of"),
    ("tier", "gold", "not one of"),
])
def test_an_unknown_enum_is_refused_rather_than_defaulted(
        repo: Path, key: str, value: str, message: str) -> None:
    make_group(repo, "commodity")
    path = groups.manifest_path(repo, "commodity")
    body = yaml.safe_load(path.read_text())
    body[key] = value
    path.write_text(yaml.safe_dump(body))

    with pytest.raises(groups.GroupError, match=message):
        groups.load(repo, "commodity")


def test_a_negative_retention_is_refused(repo: Path) -> None:
    make_group(repo, "commodity")
    path = groups.manifest_path(repo, "commodity")
    body = yaml.safe_load(path.read_text())
    body["data"]["retention_days"] = -1
    path.write_text(yaml.safe_dump(body))

    with pytest.raises(groups.GroupError, match="cannot be negative"):
        groups.load(repo, "commodity")


def test_an_absent_promise_is_none_and_not_zero(repo: Path) -> None:
    """`retention_days: null` means nothing was promised, which offboarding
    reports differently from a promise of zero days."""
    make_group(repo, "commodity")
    path = groups.manifest_path(repo, "commodity")
    body = yaml.safe_load(path.read_text())
    body["data"]["retention_days"] = None
    path.write_text(yaml.safe_dump(body))

    assert groups.load(repo, "commodity").data.retention_days is None


def test_an_unmanaged_group_is_still_visible(repo: Path) -> None:
    """Being unmanaged is a finding, not a reason to disappear from the fleet."""
    (repo / "groups" / "legacy").mkdir()
    make_group(repo, "commodity")

    assert groups.group_names(repo) == ["commodity", "legacy"]
    assert groups.unmanaged(repo) == ["legacy"]
    assert [m.group for m in groups.load_all(repo)] == ["commodity"]


# --- lifecycle ---------------------------------------------------------------


def test_the_states_that_run_loops_and_the_states_that_are_strict(repo: Path) -> None:
    make_group(repo, "commodity", lifecycle="active")
    active = groups.load(repo, "commodity")
    make_group(repo, "later", lifecycle="provisioned")
    building = groups.load(repo, "later")

    assert active.runs_loops and active.strict
    # Still being built: its loops do not run and its gates do not fail it.
    assert not building.runs_loops and not building.strict


def test_a_suspended_group_stops_running_but_stays_judged(repo: Path) -> None:
    """Paused is not the same as unfinished: the data is live, so the gates
    keep applying even though nothing runs."""
    make_group(repo, "commodity", lifecycle="suspended")
    m = groups.load(repo, "commodity")

    assert not m.runs_loops and m.strict


@pytest.mark.parametrize("start,target", [
    ("proposed", "provisioned"), ("provisioned", "active"),
    ("active", "suspended"), ("suspended", "active"),
    ("active", "offboarding"), ("offboarding", "archived"),
])
def test_legal_transitions(repo: Path, start: str, target: str) -> None:
    make_group(repo, "commodity", lifecycle=start)

    assert groups.set_lifecycle(repo, "commodity", target).lifecycle == target


@pytest.mark.parametrize("start,target", [
    ("proposed", "active"),       # nothing is live before it is provisioned
    ("active", "archived"),       # archived is only reachable through offboarding
    ("archived", "active"),       # and archived is terminal
])
def test_refused_transitions(repo: Path, start: str, target: str) -> None:
    make_group(repo, "commodity", lifecycle=start)

    with pytest.raises(groups.GroupError, match="cannot become"):
        groups.set_lifecycle(repo, "commodity", target)
    assert groups.load(repo, "commodity").lifecycle == start


def test_the_budget_falls_back_for_a_group_nobody_has_managed(repo: Path) -> None:
    """An unmanaged group keeps working on the platform default rather than
    running with no ceiling at all."""
    (repo / "groups" / "legacy").mkdir()
    make_group(repo, "commodity")
    path = groups.manifest_path(repo, "commodity")
    body = yaml.safe_load(path.read_text())
    body["budget"]["daily_tokens"] = 40_000
    path.write_text(yaml.safe_dump(body))

    assert groups.budget_for(repo, "commodity", 200_000) == 40_000
    assert groups.budget_for(repo, "legacy", 200_000) == 200_000


# --- is this family onboarded? -----------------------------------------------


def test_a_complete_active_family_passes(repo: Path) -> None:
    make_group(repo, "commodity", lifecycle="active", projects=("commodity-india",))

    report = groups.verify(repo, "commodity")

    assert report.ok and report.score == 100, [c.detail for c in report.checks
                                               if not c.passed]


def test_an_empty_active_group_fails_instead_of_passing_by_having_nothing(
        repo: Path) -> None:
    """The failure this whole check exists for: before it, a group with no
    projects passed every gate in the repo."""
    make_group(repo, "commodity", lifecycle="active")

    report = groups.verify(repo, "commodity")

    assert not report.ok
    assert "has a project" in {c.name for c in report.failures}


def test_the_same_shortfall_is_a_warning_while_the_family_is_being_built(
        repo: Path) -> None:
    make_group(repo, "commodity", lifecycle="provisioned")

    report = groups.verify(repo, "commodity")

    assert report.ok  # nothing failed
    assert "has a project" in {c.name for c in report.warnings}


def test_an_unannotated_project_fails_an_active_family(repo: Path) -> None:
    make_group(repo, "commodity", lifecycle="active",
               projects=("commodity-india",), annotated=False)

    report = groups.verify(repo, "commodity")

    assert "entities annotated" in {c.name for c in report.failures}


def test_a_family_behind_the_scaffold_is_reported_but_not_failed(repo: Path) -> None:
    """Drift is a warning whatever the lifecycle: `pf bootstrap --all` fixes it,
    and failing a live tenant for a template change is the platform's problem."""
    make_group(repo, "commodity", lifecycle="active",
               projects=("commodity-india",), template=1)

    report = groups.verify(repo, "commodity")

    warned = {c.name for c in report.warnings}
    assert "template current" in warned and report.ok


def test_a_stub_claude_md_is_caught(repo: Path) -> None:
    make_group(repo, "commodity", lifecycle="active", projects=("p",))
    (repo / "groups" / "commodity" / "CLAUDE.md").write_text(
        "# commodity\n\n## Business rules\n\n- (none yet)\n")

    report = groups.verify(repo, "commodity")

    assert "business rules written" in {c.name for c in report.warnings}


def test_an_ontology_that_disagrees_with_the_manifest_is_caught(repo: Path) -> None:
    make_group(repo, "commodity", lifecycle="active", projects=("p",))
    inst = repo / "groups" / "commodity" / "ontology" / "instance.yaml"
    inst.write_text(yaml.safe_dump({"group": "commodity", "domain": "fintech"}))

    report = groups.verify(repo, "commodity")

    assert "ontology agrees" in {c.name for c in report.failures}


def test_verify_all_reports_an_unmanaged_group_rather_than_skipping_it(
        repo: Path) -> None:
    make_group(repo, "commodity", projects=("p",))
    (repo / "groups" / "legacy").mkdir()

    reports = {r.group: r for r in groups.verify_all(repo)}

    assert reports["legacy"].error and not reports["legacy"].ok
    assert reports["commodity"].ok


# --- what leaving costs ------------------------------------------------------


def test_the_plan_sorts_what_it_finds_by_who_has_to_act(repo: Path) -> None:
    make_group(repo, "commodity", projects=("commodity-india",),
               resources={"artifact_prefix": "groups/commodity",
                          "catalog_services": ["commodity_india"]})
    wf = repo / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "commodity-india.yml").write_text("name: commodity-india\n")

    p = offboard.plan(repo, "commodity")

    removes = {i.what for i in p.of("removes")}
    assert "groups/commodity/" in removes
    assert ".github/workflows/commodity-india.yml" in removes
    manual = {i.what for i in p.of("manual")}
    assert {"artefact store objects", "dlt pipeline state", "warehouses"} <= manual


def test_a_plan_says_so_when_nothing_recorded_what_the_tenant_owned(
        repo: Path) -> None:
    """An empty `resources:` block must produce a plan that reports the gap, not
    a plan that looks clean."""
    make_group(repo, "commodity", projects=("p",), resources={})

    detail = {i.what: i.detail for i in offboard.plan(repo, "commodity").of("manual")}

    assert "nothing records" in detail["artefact store objects"]
    assert "no catalog_services" in detail["OpenMetadata services"]


def test_the_plan_removes_nothing(repo: Path) -> None:
    make_group(repo, "commodity", projects=("commodity-india",))
    wf = repo / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "commodity-india.yml").write_text("name: x\n")

    offboard.plan(repo, "commodity")

    assert (repo / "groups" / "commodity").is_dir()
    assert (wf / "commodity-india.yml").is_file()


def test_apply_refuses_a_group_that_has_not_been_moved_to_offboarding(
        repo: Path) -> None:
    """The state is the deliberate step; without it this is one typo away from
    deleting a live tenant."""
    make_group(repo, "commodity", lifecycle="active", projects=("p",))

    with pytest.raises(groups.GroupError, match="offboarding"):
        offboard.apply(repo, "commodity")
    assert (repo / "groups" / "commodity").is_dir()


def test_apply_removes_what_the_repo_owns_and_leaves_a_tombstone(repo: Path) -> None:
    make_group(repo, "commodity", lifecycle="offboarding",
               projects=("commodity-india",),
               resources={"artifact_prefix": "groups/commodity"})
    wf = repo / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "commodity-india.yml").write_text("name: commodity-india\n")

    removed, stone = offboard.apply(repo, "commodity")

    assert not (repo / "groups" / "commodity").exists()
    assert not (wf / "commodity-india.yml").exists()
    assert ".github/workflows/commodity-india.yml" in removed
    body = (repo / stone).read_text()
    # The tombstone keeps what the family promised, so a later question about a
    # departed tenant has somewhere to land.
    assert "archived_at:" in body and "commodity" in body
    assert "erasure_sla_days: 30" in body


def test_apply_can_keep_the_directory_for_an_export_first(repo: Path) -> None:
    make_group(repo, "commodity", lifecycle="offboarding", projects=("p",))
    wf = repo / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "p.yml").write_text("name: p\n")

    offboard.apply(repo, "commodity", keep_directory=True)

    assert (repo / "groups" / "commodity").is_dir()
    assert not (wf / "p.yml").exists()


def test_an_unmanaged_group_cannot_be_offboarded_by_this_command(repo: Path) -> None:
    (repo / "groups" / "legacy").mkdir()

    with pytest.raises(groups.GroupError):
        offboard.apply(repo, "legacy")
    plan = offboard.plan(repo, "legacy")
    assert plan.blockers and plan.lifecycle == "unmanaged"


# --- PII held to no deadline -------------------------------------------------


def test_pii_in_a_group_with_no_retention_promise_is_a_finding(
        repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The graph has known which columns are PII all along. What was missing was
    anything saying how long this family may keep them."""
    from pf.loops import registry
    from pf.loops.runner import LoopRun

    make_group(repo, "commodity", projects=("commodity-india",))
    path = groups.manifest_path(repo, "commodity")
    body = yaml.safe_load(path.read_text())
    body["data"]["retention_days"] = None
    body["data"]["erasure_sla_days"] = None
    path.write_text(yaml.safe_dump(body))

    # Stand in for the graph: one PII column that reaches a mart.
    monkeypatch.setattr(registry, "open_graph", None, raising=False)
    kg = repo / "groups" / "commodity" / "projects" / "commodity-india" / "kg"
    kg.mkdir(parents=True)
    (kg / "graph.duckdb").write_bytes(b"")

    class _Col:
        id, name = "col.1", "email"
        props: ClassVar[dict] = {"pii": True, "model": "fct_orders"}

    class _Model:
        id, layer = "model.fct_orders", "marts"

    class _Edge:
        src = "model.fct_orders"

    class _Graph:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def nodes(self, kind):
            return [_Model()] if kind == "Model" else [_Col()]

        def in_edges(self, _):
            return [_Edge()]

    monkeypatch.setattr("pf.kg.store.open_graph", lambda *a, **k: _Graph())

    run = LoopRun(run_id="x", loop="pii-audit", group="commodity",
                  project="commodity-india", started_at="2026-01-01T00:00:00+00:00")
    findings = registry.pii_audit(repo, "commodity", "commodity-india", run)

    assert any("no stated deadline" in f for f in findings)
    assert any("retention_days" in f and "erasure_sla_days" in f for f in findings)
