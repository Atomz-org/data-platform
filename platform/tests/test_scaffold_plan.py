"""Tests for `pf new-project --plan`.

The plan exists to be trusted without being tried. That puts two obligations on
it, and both are easy to lose quietly:

  it must write nothing            a "dry run" that leaves a directory behind is
                                     worse than no dry run, because the next
                                     apply then refuses on the mess it made
  it must catch what actually      a plan listing what *would* happen but not
    fails                            what would *stop* it is a plan you still
                                     have to try before you believe

The two blockers below are not hypothetical. Scaffolding into a directory that
already holds a project, and scaffolding a sister into a group that does not
exist, are the failures this command was added for.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pf.capabilities import CAPABILITIES
from pf.scaffold import plan as planner


def _root(tmp_path: Path, group: str = "acme") -> Path:
    (tmp_path / "platform").mkdir(exist_ok=True)
    (tmp_path / "groups" / group / "projects").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _caps(*names: str):
    return [CAPABILITIES[n] for n in names if n in CAPABILITIES]


# ------------------------------------------------------------- blockers -----
def test_a_missing_group_blocks_and_names_the_fix(tmp_path: Path) -> None:
    (tmp_path / "platform").mkdir()
    (tmp_path / "groups").mkdir()

    p = planner.build(tmp_path, "nosuch", "demo-us", _caps("github"))

    assert not p.ok
    assert any("does not exist" in b for b in p.blockers)
    assert "pf new-group nosuch" in planner.render(p), "a blocker must name its fix"


def test_an_existing_project_blocks_rather_than_overwriting(tmp_path: Path) -> None:
    """The scaffolder would happily write over a live project otherwise."""
    root = _root(tmp_path)
    pdir = root / "groups" / "acme" / "projects" / "acme-us"
    (pdir / "transform").mkdir(parents=True)
    (pdir / "transform" / "dbt_project.yml").write_text("name: acme_us\n")

    p = planner.build(root, "acme", "acme-us", _caps("github"))

    assert not p.ok
    blocker = " ".join(p.blockers)
    assert "already exists" in blocker
    assert "1 file(s)" in blocker, "say how much is there, so the risk is legible"
    # The two ways forward, because "blocked" without a route is a dead end.
    assert "pf bootstrap" in blocker and "pf capability-add" in blocker


def test_a_clean_target_is_not_blocked(tmp_path: Path) -> None:
    root = _root(tmp_path)

    p = planner.build(root, "acme", "acme-us", _caps("github"))

    assert p.ok
    assert not p.blockers


# ------------------------------------------------------------- warnings -----
def test_missing_credentials_warn_but_do_not_block(tmp_path: Path,
                                                   monkeypatch: pytest.MonkeyPatch) -> None:
    """A production target is inert until `DBT_TARGET=prod` asks for it.

    Blocking here would stop a laptop scaffolding a project whose warehouse it
    will never connect to, which is every project at creation time.
    """
    root = _root(tmp_path)
    for var in ("SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_DATABASE"):
        monkeypatch.delenv(var, raising=False)

    p = planner.build(root, "acme", "acme-us", _caps("snowflake"))

    assert p.ok, "missing credentials must not block a scaffold"
    assert any("needs unset env" in w for w in p.warnings)


def test_a_rollup_over_no_sisters_warns(tmp_path: Path) -> None:
    """A roll-up unions its sisters, so a group with none unions nothing."""
    root = _root(tmp_path)

    p = planner.build(root, "acme", "acme-rollup", _caps("github"), is_rollup=True)

    assert p.ok
    assert any("no sister projects" in w for w in p.warnings)


def test_a_rollup_with_sisters_is_quiet(tmp_path: Path) -> None:
    root = _root(tmp_path)
    (root / "groups" / "acme" / "projects" / "acme-us").mkdir(parents=True)

    p = planner.build(root, "acme", "acme-rollup", _caps("github"), is_rollup=True)

    assert not any("no sister projects" in w for w in p.warnings)


# --------------------------------------------------------------- render -----
def test_the_plan_is_cheaper_than_the_registry_it_replaces(tmp_path: Path) -> None:
    """Its whole reason for existing is that reading is dearer than asking.

    `pf capabilities` is ~960 tokens and the capability module is far more. If
    the plan ever approaches that, it has stopped being the cheap path.
    """
    root = _root(tmp_path)
    p = planner.build(root, "acme", "acme-us", list(CAPABILITIES.values()))

    approx_tokens = len(planner.render(p)) // 4

    assert approx_tokens < 400, (
        f"the plan is ~{approx_tokens} tokens; summarise rather than enumerate")


def test_the_plan_names_every_enabled_capability(tmp_path: Path) -> None:
    root = _root(tmp_path)
    caps = _caps("github", "evidence")

    out = planner.render(planner.build(root, "acme", "acme-us", caps))

    for c in caps:
        assert c.name in out
    assert "impact-gate" in out, "the CI a project will run is part of the decision"


def test_an_empty_capability_set_is_stated_not_omitted(tmp_path: Path) -> None:
    """`--without` everything is legal and unusual; silence would read as a bug."""
    root = _root(tmp_path)

    out = planner.render(planner.build(root, "acme", "acme-us", []))

    assert "nothing" in out


def test_render_is_stable_for_a_fixed_input(tmp_path: Path) -> None:
    """Capability order comes from a dict; the plan must not inherit that."""
    root = _root(tmp_path)
    caps = _caps("snowflake", "github", "evidence")

    first = planner.render(planner.build(root, "acme", "acme-us", caps))
    second = planner.render(planner.build(root, "acme", "acme-us", list(reversed(caps))))

    assert first == second


# ------------------------------------------------------------ side effects --
def test_building_a_plan_writes_nothing(tmp_path: Path) -> None:
    """The one property that makes a dry run worth having."""
    root = _root(tmp_path)
    before = set(root.rglob("*"))

    planner.render(planner.build(root, "acme", "acme-us", list(CAPABILITIES.values())))

    assert set(root.rglob("*")) == before
