"""Elementary tool + the shared dbt-file editors it is built on.

The properties worth pinning: an edit to a project-owned file must be
idempotent, must never fight a human's pin, and must never delete a human's
comment — those are the failure modes that turn `pf bootstrap` from a retrofit
into a hazard.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pf.tools import dbtproject, registry
from pf.tools import elementary as el

DBT_PROJECT = """\
name: 'demo'
version: '1.0.0'
config-version: 2
profile: 'demo'

# A comment a human wrote, explaining a real decision.
macro-paths: ["macros"]

models:
  demo:
    marts:
      +materialized: table
"""

PACKAGES = """\
packages:
- package: dbt-labs/dbt_utils
  version:
  - '>=1.3.0'
  - <2.0.0
"""

PROFILES = """\
demo:
  target: "{{ env_var('DBT_TARGET', 'dev') }}"
  outputs:
    dev:
      type: duckdb
      path: "{{ env_var('PF_DUCKDB_PATH') }}"
"""


def _project(tmp_path: Path) -> Path:
    d = tmp_path / "groups" / "g" / "projects" / "p"
    t = d / "transform"
    t.mkdir(parents=True)
    (t / "dbt_project.yml").write_text(DBT_PROJECT)
    (t / "packages.yml").write_text(PACKAGES)
    (t / "profiles.yml").write_text(PROFILES)
    return d


# ------------------------------------------------------------- dbtproject --
def test_ensure_package_adds_once_and_respects_existing_pins(tmp_path: Path) -> None:
    d = _project(tmp_path) / "transform"
    assert dbtproject.ensure_package(d, "org/pkg", [">=1.0.0", "<2.0.0"])
    assert not dbtproject.ensure_package(d, "org/pkg", [">=1.0.0", "<2.0.0"])

    doc = yaml.safe_load((d / "packages.yml").read_text())
    entries = {e["package"]: e for e in doc["packages"]}
    # The pre-existing pin is byte-for-byte the project's own decision.
    assert entries["dbt-labs/dbt_utils"]["version"] == [">=1.3.0", "<2.0.0"]
    assert entries["org/pkg"]["version"] == [">=1.0.0", "<2.0.0"]


def test_ensure_package_never_touches_a_declared_version(tmp_path: Path) -> None:
    d = _project(tmp_path) / "transform"
    before = (d / "packages.yml").read_text()
    assert not dbtproject.ensure_package(d, "dbt-labs/dbt_utils", [">=9.9.9"])
    assert (d / "packages.yml").read_text() == before


def test_dependencies_yml_counts_as_declared(tmp_path: Path) -> None:
    d = _project(tmp_path) / "transform"
    (d / "dependencies.yml").write_text(
        "packages:\n- package: org/pkg\n  version: ['1.0.0']\n")
    assert not dbtproject.ensure_package(d, "org/pkg", [">=1.0.0"])


def test_insert_under_key_preserves_comments(tmp_path: Path) -> None:
    d = _project(tmp_path) / "transform"
    path = d / "dbt_project.yml"
    assert dbtproject.insert_under_key(path, "models", "  extra:\n    +schema: x\n")

    text = path.read_text()
    assert "# A comment a human wrote" in text
    doc = yaml.safe_load(text)
    assert doc["models"]["extra"]["+schema"] == "x"
    assert doc["models"]["demo"]["marts"]["+materialized"] == "table"


def test_insert_under_missing_key_appends_a_valid_block(tmp_path: Path) -> None:
    d = _project(tmp_path) / "transform"
    path = d / "dbt_project.yml"
    assert dbtproject.insert_under_key(path, "vars", "  a: 1\n")
    assert yaml.safe_load(path.read_text())["vars"]["a"] == 1


def test_append_profile_is_idempotent_and_additive(tmp_path: Path) -> None:
    d = _project(tmp_path) / "transform"
    assert dbtproject.append_profile(d, "extra", "extra:\n  target: t\n")
    assert not dbtproject.append_profile(d, "extra", "extra:\n  target: t\n")
    doc = yaml.safe_load((d / "profiles.yml").read_text())
    assert set(doc) == {"demo", "extra"}


# -------------------------------------------------------------- elementary --
def test_bootstrap_declares_package_config_and_profile(tmp_path: Path) -> None:
    d = _project(tmp_path)
    r = el.bootstrap_project(tmp_path, "g", "p", d, {})
    assert r.status == "ok"

    t = d / "transform"
    pkgs = yaml.safe_load((t / "packages.yml").read_text())
    assert any(e["package"] == el.PACKAGE for e in pkgs["packages"])

    proj = yaml.safe_load((t / "dbt_project.yml").read_text())
    assert proj["models"]["elementary"]["+schema"] == "elementary"
    # The pre-existing model config and the human comment both survived.
    assert proj["models"]["demo"]["marts"]["+materialized"] == "table"
    assert "# A comment a human wrote" in (t / "dbt_project.yml").read_text()

    profiles = yaml.safe_load((t / "profiles.yml").read_text())
    # Derived, not static: the elementary profile mirrors the project's own
    # targets, schema suffixed the way dbt composes custom schemas.
    dev = profiles["elementary"]["outputs"]["dev"]
    assert dev["type"] == "duckdb"
    assert dev["path"] == "{{ env_var('PF_DUCKDB_PATH') }}"
    assert dev["schema"] == "main_elementary"


def test_bootstrap_is_idempotent(tmp_path: Path) -> None:
    d = _project(tmp_path)
    el.bootstrap_project(tmp_path, "g", "p", d, {})
    snapshot = {f.name: f.read_text()
                for f in (d / "transform").glob("*.yml")}
    r = el.bootstrap_project(tmp_path, "g", "p", d, {})
    assert r.status == "ok" and "unchanged" in r.detail
    assert snapshot == {f.name: f.read_text()
                        for f in (d / "transform").glob("*.yml")}


def test_bootstrap_skips_a_project_with_no_dbt(tmp_path: Path) -> None:
    d = tmp_path / "groups" / "g" / "projects" / "empty"
    d.mkdir(parents=True)
    assert el.bootstrap_project(tmp_path, "g", "empty", d, {}).status == "skipped"


def test_registered_ordered_after_recce_and_gate_safe() -> None:
    tools = registry.all_tools()
    assert "elementary" in tools
    t = tools["elementary"]
    # Recce's bootstrap can regenerate profiles.yml wholesale; the elementary
    # profile only survives a fresh scaffold if it is appended afterwards.
    assert "recce" in t.after
    assert t.offline and t.default_enabled
    assert t.gate_sections() == {"denylist": ["**/transform/edr_target/**"]}


# -------------------------------------------------------- derived profile --
def test_profile_mirrors_every_production_engine() -> None:
    """One elementary output per project target, connection identical, schema
    suffixed per dbt's default naming — including BigQuery, which calls the
    same idea `dataset`. This is what makes `edr` work against whichever
    warehouse `DBT_TARGET` selects, instead of dev-only."""
    doc = el.derive_profile({
        "demo": {
            "target": "{{ env_var('DBT_TARGET', 'dev') }}",
            "outputs": {
                "dev": {"type": "duckdb",
                        "path": "{{ env_var('PF_DUCKDB_PATH') }}"},
                "prod": {"type": "snowflake",
                         "account": "{{ env_var('SNOWFLAKE_ACCOUNT') }}",
                         "schema": "{{ env_var('SNOWFLAKE_SCHEMA', 'ANALYTICS') }}"},
            },
        },
    })
    out = doc["elementary"]["outputs"]
    assert doc["elementary"]["target"] == "{{ env_var('DBT_TARGET', 'dev') }}"
    assert out["dev"]["schema"] == "main_elementary"
    assert out["prod"]["type"] == "snowflake"
    assert out["prod"]["account"] == "{{ env_var('SNOWFLAKE_ACCOUNT') }}"
    assert out["prod"]["schema"] == "{{ env_var('SNOWFLAKE_SCHEMA', 'ANALYTICS') }}_elementary"

    bq = el.derive_profile({"demo": {"outputs": {"prod": {
        "type": "bigquery", "dataset": "analytics"}}}})
    assert bq["elementary"]["outputs"]["prod"]["dataset"] == "analytics_elementary"

    lake = el.derive_profile({"demo": {"outputs": {"prod": {
        "type": "duckdb", "path": "ducklake:{{ env_var('DUCKLAKE_METADATA') }}",
        "schema": "analytics"}}}})
    prod = lake["elementary"]["outputs"]["prod"]
    assert prod["path"].startswith("ducklake:")
    assert prod["schema"] == "analytics_elementary"


def test_retargeting_the_project_retargets_edr(tmp_path: Path) -> None:
    """Swap prod to another warehouse after elementary is set up: the next
    bootstrap must re-derive the block, or edr reports on a warehouse the
    project no longer builds in."""
    from pf.runtime.targets import WAREHOUSES
    from pf.scaffold.generator import PROJECT_TARGETS, render_profiles

    d = _project(tmp_path)
    t = d / "transform"
    el.bootstrap_project(tmp_path, "g", "p", d, {})
    first = yaml.safe_load((t / "profiles.yml").read_text())
    assert "prod" not in first["elementary"]["outputs"]  # fixture has dev only

    # The ducklake capability replaces the project profile wholesale (which
    # also drops the elementary block — exactly the drift being tested).
    (t / "profiles.yml").write_text(render_profiles(
        "demo", {**PROJECT_TARGETS, "prod": WAREHOUSES["ducklake"].output}))
    r = el.bootstrap_project(tmp_path, "g", "p", d, {})
    assert "profiles.yml" in r.detail

    doc = yaml.safe_load((t / "profiles.yml").read_text())
    prod = doc["elementary"]["outputs"]["prod"]
    assert prod["path"] == "ducklake:{{ env_var('DUCKLAKE_METADATA') }}"
    assert prod["schema"] == "{{ env_var('DUCKLAKE_SCHEMA', 'analytics') }}_elementary"
    # The project's own targets are untouched by the derivation.
    assert doc["demo"]["outputs"]["dev"]["path"] == "{{ env_var('PF_DUCKDB_PATH') }}"


def test_replace_profile_swaps_stale_block_and_its_comments(tmp_path: Path) -> None:
    d = _project(tmp_path) / "transform"
    (d / "profiles.yml").write_text(
        PROFILES
        + "\n# old explanation line one\n# and two\nelementary:\n"
          "  target: default\n  outputs:\n    default: {type: duckdb}\n")
    assert dbtproject.replace_profile(d, "elementary", "elementary:\n  target: dev\n")
    text = (d / "profiles.yml").read_text()
    assert "old explanation" not in text and "default: {type: duckdb}" not in text
    doc = yaml.safe_load(text)
    assert doc["elementary"] == {"target": "dev"}
    assert doc["demo"]["outputs"]["dev"]["type"] == "duckdb"
