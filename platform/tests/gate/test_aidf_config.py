"""AIDF configuration: the floor governs every entity, overlays only tighten.

  no file is not no governance   a project with no aidf.yaml resolves to the
                                   platform floor, so a project scaffolded before
                                   the capability existed is still governed

  a layer may only tighten       a budget can go down and not up, a patch window
                                   can shrink and not grow, a validator can be
                                   added and not removed, scope can be declined
                                   only with a reason and an owner

  the capability reaches         it is default-enabled, its seeded file is
    every project                  inert on arrival, and its gate rules are
                                   in the generated overlay
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from conftest import REPO_ROOT
from pf.aidf.config import (
    DEFAULTS_FILE,
    AidfConfigError,
    AidfRelaxation,
    defaults,
    entities,
    layer_paths,
    load,
)
from pf.capabilities import CAPABILITIES, render
from pf.capabilities import defaults as default_caps


def _repo(tmp_path: Path, group_overlay: dict | None = None, project_overlay: dict | None = None) -> Path:
    (tmp_path / "groups" / "g" / "projects" / "p" / "governance").mkdir(parents=True, exist_ok=True)
    (tmp_path / "platform").mkdir(exist_ok=True)
    if group_overlay is not None:
        (tmp_path / "groups" / "g" / "aidf.yaml").write_text(yaml.safe_dump(group_overlay))
    if project_overlay is not None:
        (tmp_path / "groups" / "g" / "projects" / "p" / "governance" / "aidf.yaml").write_text(
            yaml.safe_dump(project_overlay))
    return tmp_path


# ------------------------------------------------------------------ floor --

def test_floor_is_well_formed() -> None:
    d = defaults()
    assert d["version"] == 1
    assert set(d) == {"version", "runtime", "dora"}
    assert d["runtime"]["validators"][0] == "schema", "the contract is always checked first"
    assert d["dora"]["sbom"]["grace_days"]["critical"] == 0, "zero tolerance on critical by default"
    assert d["dora"]["provider"] == "", "the floor names no cloud — that is the entity's fact"


def test_no_overlay_resolves_to_the_floor(tmp_path: Path) -> None:
    cfg = load(_repo(tmp_path), "g", "p")
    assert cfg.doc == defaults()
    assert len(cfg.layers) == 1 and cfg.layers[0].endswith("aidf/data/defaults.yaml")
    assert cfg.dialect == "duckdb" and cfg.in_scope and "metric-gap-harvester" in cfg.roles


def test_layer_paths_are_floor_group_project(tmp_path: Path) -> None:
    paths = layer_paths(tmp_path, "g", "p")
    assert paths[0] == DEFAULTS_FILE
    assert paths[1] == tmp_path / "groups" / "g" / "aidf.yaml"
    assert paths[2] == tmp_path / "groups" / "g" / "projects" / "p" / "governance" / "aidf.yaml"


# ------------------------------------------------------------- tightening --

def test_group_then_project_layer_in_order(tmp_path: Path) -> None:
    root = _repo(tmp_path,
                 {"runtime": {"budgets": {"max_consecutive_validation_failures": 2}}},
                 {"runtime": {"sql_dialect": "snowflake", "budgets": {"max_consecutive_validation_failures": 1}}})
    cfg = load(root, "g", "p")
    assert cfg.dialect == "snowflake"
    assert cfg.budgets["max_consecutive_validation_failures"] == 1
    assert len(cfg.layers) == 3


@pytest.mark.parametrize("overlay", [
    {"runtime": {"budgets": {"max_consecutive_validation_failures": 99}}},
    {"runtime": {"budgets": {"max_iterations_per_invocation": 500}}},
    {"dora": {"sbom": {"grace_days": {"critical": 30}}}},
    {"dora": {"prowler": {"fail_on": {"critical": 100}}}},
    {"dora": {"prowler": {"severity_threshold": "critical"}}},
    {"runtime": {"budgets": {"trip_circuit_breaker_on_breach": False}}},
])
def test_loosening_is_refused(tmp_path: Path, overlay: dict) -> None:
    with pytest.raises(AidfRelaxation):
        load(_repo(tmp_path, project_overlay=overlay), "g", "p")


def test_boolean_directions_are_pinned(tmp_path: Path) -> None:
    """`ignore_unfixed: false` blocks on more, so it loads; switching the
    breaker off blocks on less, so it does not. Pinned because the two flags
    read alike and tighten in opposite directions."""
    cfg = load(_repo(tmp_path, project_overlay={"dora": {"sbom": {"ignore_unfixed": False}}}), "g", "p")
    assert cfg.dora["sbom"]["ignore_unfixed"] is False
    root = _repo(tmp_path / "second", {"dora": {"sbom": {"ignore_unfixed": False}}},
                 {"dora": {"sbom": {"ignore_unfixed": True}}})
    with pytest.raises(AidfRelaxation):
        load(root, "g", "p")


def test_tightening_is_allowed(tmp_path: Path) -> None:
    root = _repo(tmp_path, project_overlay={
        "runtime": {"budgets": {"max_consecutive_validation_failures": 1}, "validators": ["extra_check"],
                    "mart_pattern": "^fct_[a-z_]+$"},
        "dora": {"sbom": {"grace_days": {"medium": 7}}, "prowler": {"severity_threshold": "medium"}},
    })
    cfg = load(root, "g", "p")
    assert cfg.budgets["max_consecutive_validation_failures"] == 1
    assert cfg.validators == ("schema", "sql_ast", "pii", "extra_check"), "validators union, never replace"
    assert cfg.mart_pattern == "^fct_[a-z_]+$"
    assert cfg.dora["sbom"]["grace_days"]["medium"] == 7
    assert cfg.dora["sbom"]["grace_days"]["critical"] == 0, "untouched keys keep the floor"


def test_validators_cannot_be_removed(tmp_path: Path) -> None:
    cfg = load(_repo(tmp_path, project_overlay={"runtime": {"validators": ["schema"]}}), "g", "p")
    assert "sql_ast" in cfg.validators and "pii" in cfg.validators


def test_out_of_scope_needs_reason_and_owner(tmp_path: Path) -> None:
    with pytest.raises(AidfRelaxation):
        load(_repo(tmp_path, project_overlay={"dora": {"in_scope": False}}), "g", "p")
    cfg = load(_repo(tmp_path, project_overlay={
        "dora": {"in_scope": False, "out_of_scope_reason": "not a financial entity", "owner": "risk@example.com"}}),
        "g", "p")
    assert not cfg.in_scope


def test_article_opt_out_needs_reason_and_owner(tmp_path: Path) -> None:
    with pytest.raises(AidfRelaxation):
        load(_repo(tmp_path, project_overlay={"dora": {"articles": {"28": {"applies": False}}}}), "g", "p")
    cfg = load(_repo(tmp_path, project_overlay={
        "dora": {"articles": {"28": {"applies": False, "reason": "no third party", "owner": "a@b.c"}}}}), "g", "p")
    assert cfg.article_applies("28") == (False, "no third party")
    assert cfg.article_applies("5") == (True, "")


def test_exception_needs_id_reason_owner_expiry(tmp_path: Path) -> None:
    with pytest.raises(AidfConfigError):
        load(_repo(tmp_path, project_overlay={"dora": {"sbom": {"exceptions": [{"id": "CVE-1"}]}}}), "g", "p")


def test_unknown_top_level_key_is_refused(tmp_path: Path) -> None:
    with pytest.raises(AidfConfigError):
        load(_repo(tmp_path, project_overlay={"governance": {}}), "g", "p")


def test_entities_lists_every_project(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    (root / "groups" / "g" / "projects" / "q").mkdir()
    (root / "groups" / ".hidden" / "projects" / "x").mkdir(parents=True)
    assert entities(root) == [("g", "p"), ("g", "q")]


def test_every_real_entity_resolves() -> None:
    """The CI guarantee: no project in the checkout carries an overlay that
    will not load, whether or not it has one."""
    for g, p in entities(REPO_ROOT):
        load(REPO_ROOT, g, p)


# ------------------------------------------------------------- capability --

def test_capability_is_default_enabled_and_requires_its_neighbours() -> None:
    cap = CAPABILITIES["aidf"]
    assert "aidf" in default_caps()
    assert set(cap.requires) == {"governance", "air"}
    assert "governance/aidf.yaml" in cap.preserve, "the entity owns its overlay; re-applying must not overwrite it"


def test_seeded_overlay_is_inert(tmp_path: Path) -> None:
    """Applying the capability to any project changes no verdict: the rendered
    file must resolve to exactly the floor."""
    cap = CAPABILITIES["aidf"]
    rendered = render(cap.files["governance/aidf.yaml"], {"group": "g", "project": "p"})
    doc = yaml.safe_load(rendered)
    root = _repo(tmp_path)
    (root / "groups" / "g" / "projects" / "p" / "governance" / "aidf.yaml").write_text(rendered)
    cfg = load(root, "g", "p")
    floor = defaults()
    assert doc["version"] == 1
    assert cfg.runtime == floor["runtime"]
    assert cfg.dora == floor["dora"]


def test_capability_gate_rules_are_in_the_generated_overlay() -> None:
    overlay = yaml.safe_load((REPO_ROOT / "gate.capabilities.yaml").read_text())
    assert "**/governance/dora/**" in overlay["denylist"]
    assert "**/governance/aidf.yaml" in overlay["impact_required"]


def test_capability_policies_are_in_the_generated_overlay() -> None:
    doc = yaml.safe_load((REPO_ROOT / "platform" / "src" / "pf" / "ontology" / "policy.capabilities.yaml").read_text())
    ids = {p["id"] for p in doc["policies"]}
    assert {"agent-output-passes-contract", "agent-sql-is-read-only", "dora-patch-window-enforced"} <= ids
    for p in doc["policies"]:
        if p["_capability"] == "aidf":
            assert p["enforced_by"], "an aidf obligation names what enforces it"
