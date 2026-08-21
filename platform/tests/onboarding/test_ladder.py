"""Tests for the onboarding ladder.

What is worth pinning here is not that the stages run — it is the handful of
decisions that make the ladder mean anything, each of which was wrong at some
point during its construction:

  * a gate that is derived, so it cannot report a pass that a later change
    invalidated;
  * `unexercised` as a third verdict, so a missing CLI is never reported as
    green;
  * the ladder stopping at the first closed gate, so downstream stages do not
    report findings that a fix upstream will erase;
  * a checker that judges the change rather than the result, and that knows when
    it has no baseline to judge against.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from conftest import REPO_ROOT
from pf.onboard.ladder import (
    LAYERS,
    STAGES,
    TARGET_TYPES,
    Check,
    Ctx,
    Verdict,
    check_layers,
    eval_layers,
    failed,
    ladder,
    passed,
    unexercised,
    verify,
)

ROOT = REPO_ROOT


# ------------------------------------------------------------- the ladder ----
def test_stage_names_are_unique_and_ordered() -> None:
    names = [s.name for s in STAGES]
    assert names == ["import", "ontology", "dialect", "layers", "metrics", "review"]


def test_every_stage_declares_what_it_may_write() -> None:
    """A stage that may touch anything cannot be scope-checked, and a checker
    that cannot check scope approves drive-by refactors."""
    for s in STAGES:
        assert s.owns, f"{s.name} declares no owned paths"


def test_every_stage_reference_exists() -> None:
    """A remedy pointing at a document nobody wrote is worse than no remedy."""
    base = ROOT / "platform" / "toolkits" / "project-onboarding" / "skills" / "onboard-project"
    for s in STAGES:
        assert (base / s.reference).exists(), f"{s.name} -> {s.reference}"


def test_ladder_stops_at_the_first_closed_gate(tmp_path: Path) -> None:
    """A project whose SQL will not compile has no manifest, so the metric stage
    would report 'no metrics' when the truth is 'not yet knowable'."""
    (tmp_path / "groups" / "g" / "projects" / "p").mkdir(parents=True)
    rungs = ladder(tmp_path, "g", "p")
    assert len(rungs) == 1
    assert rungs[0][0].name == "import"
    assert not rungs[0][1].open


# ---------------------------------------------------------------- verdicts ----
def test_unexercised_does_not_close_the_gate() -> None:
    """A missing MetricFlow CLI must not wall a project off from the ladder."""
    v = Verdict("metrics", [passed("a", "x"), unexercised("b", "not installed")])
    assert v.open
    assert not v.complete
    assert "not exercised" in v.summary


def test_unexercised_is_never_reported_as_a_pass() -> None:
    v = Verdict("metrics", [unexercised("b", "not installed")])
    assert v.gaps and not v.failures
    assert not v.complete


def test_one_failure_closes_the_gate() -> None:
    v = Verdict("x", [passed("a", ""), failed("b", "why"), unexercised("c", "")])
    assert not v.open and not v.complete
    assert [c.name for c in v.failures] == ["b"]


def test_check_ok_treats_unexercised_as_not_a_failure() -> None:
    assert Check("n", "unexercised", "").ok
    assert not Check("n", "fail", "").ok


# ------------------------------------------------------------------ layers ----
def _project(tmp_path: Path, models: dict[str, str],
             config: dict | None = None) -> Ctx:
    pdir = tmp_path / "groups" / "g" / "projects" / "p"
    for rel, sql in models.items():
        f = pdir / "transform" / "models" / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(sql)
    cfg = {"models": {"p": config if config is not None
                      else {"staging": {}, "marts": {}}}}
    (pdir / "transform" / "dbt_project.yml").write_text(yaml.safe_dump(cfg))
    return Ctx(root=tmp_path, group="g", project="p")


def test_staging_that_joins_is_a_finding(tmp_path: Path) -> None:
    """Staging is 1:1 with a raw table. A join there hides a business decision in
    a layer the platform treats as mechanical, and `pf gen-staging` overwrites it."""
    c = _project(tmp_path, {
        "staging/stg_a.sql": "select * from {{ source('s', 'a') }}",
        "staging/stg_joined.sql":
            "select * from {{ ref('stg_a') }} join {{ ref('stg_b') }} using (id)",
    })
    kinds = {r.kind for r in eval_layers(c)}
    assert "staging-not-1to1" in kinds
    one_to_one = next(x for x in check_layers(c) if x.name == "staging is 1:1 with raw")
    assert not one_to_one.ok


def test_one_upstream_referenced_twice_is_still_one_to_one(tmp_path: Path) -> None:
    """A CTE that reads the same upstream twice is not a join. Counting call
    sites rather than distinct targets would report every self-referencing
    staging model as a violation."""
    c = _project(tmp_path, {
        "staging/stg_a.sql":
            "with x as (select * from {{ ref('r') }}), "
            "y as (select * from {{ ref('r') }}) select * from x union all select * from y",
    })
    assert "staging-not-1to1" not in {r.kind for r in eval_layers(c)}


def test_unknown_layer_directory_is_blocking(tmp_path: Path) -> None:
    c = _project(tmp_path, {"intermediate/int_a.sql": "select 1"})
    findings = {r.kind: r for r in eval_layers(c)}
    assert findings["layer-foreign"].blocking


def test_known_layers_are_the_ones_the_platform_reasons_about() -> None:
    assert set(LAYERS) == {"staging", "marts", "semantic", "utils"}


def test_populated_layer_without_config_is_blocking(tmp_path: Path) -> None:
    """Without a block it builds with dbt's defaults instead of the platform's
    materialisation and schema, and the layer separation stops existing."""
    c = _project(tmp_path, {"marts/fct_a.sql": "select 1"}, config={"staging": {}})
    assert {r.kind for r in eval_layers(c)} >= {"layer-unconfigured"}


# ----------------------------------------------------------------- targets ----
def test_development_targets_are_credential_free() -> None:
    """A developer who needs a warehouse account to run the project stops running
    the project."""
    assert TARGET_TYPES["dev"] == "duckdb"
    assert TARGET_TYPES["base"] == "duckdb"
    assert TARGET_TYPES["prod"] is None, "production is declared per project"


# ----------------------------------------------------------------- checker ----
def test_checker_reports_no_baseline_rather_than_failing(tmp_path: Path) -> None:
    """Nothing about a freshly imported project is committed, so every file in it
    is 'changed'. Failing the size check on a 1,200-file import that was supposed
    to add 1,200 files would be a lie dressed as rigour."""
    import subprocess

    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    c = _project(tmp_path, {"marts/fct_a.sql": "select 1"})
    stage = next(s for s in STAGES if s.name == "layers")
    names = {x.name: x for x in verify(c, stage)}
    assert names["changes stay in scope"].status == "unexercised"
    assert names["change is reviewable"].status == "unexercised"


def test_checker_is_quiet_when_nothing_changed(tmp_path: Path) -> None:
    import subprocess

    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    c = Ctx(root=tmp_path, group="g", project="p")
    (tmp_path / "groups" / "g" / "projects" / "p").mkdir(parents=True)
    stage = next(s for s in STAGES if s.name == "layers")
    assert [x.status for x in verify(c, stage)] == ["unexercised"]


# -------------------------------------------------------------------- misc ----
@pytest.mark.parametrize("stage", STAGES, ids=lambda s: s.name)
def test_evaluate_and_validate_never_raise_on_an_empty_project(
    stage, tmp_path: Path
) -> None:
    """The ladder runs against half-built projects by definition. A stage that
    raises instead of reporting takes the whole report down with it."""
    (tmp_path / "groups" / "g" / "projects" / "p" / "transform").mkdir(parents=True)
    c = Ctx(root=tmp_path, group="g", project="p")
    assert isinstance(stage.evaluate(c), list)
    assert isinstance(stage.validate(c), list)
