"""Production warehouse registry — the invariants its docstring promises.

"Adding ClickHouse is one entry and no other edit" is a claim about seams, and
claims about seams rot silently: the entry gets added, the pyproject extra gets
forgotten, and `uv sync --extra <name>` — the exact command the generated docs
tell the operator to run — fails a quarter later. These tests make the
registration mechanical.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
import yaml
from pf.capabilities import CAPABILITIES
from pf.runtime.targets import WAREHOUSES, default_warehouse
from pf.scaffold.generator import PROJECT_TARGETS, render_profiles

ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------- registry ----
def test_exactly_one_warehouse_is_the_default() -> None:
    defaults = [w.name for w in WAREHOUSES.values() if w.default_enabled]
    assert defaults == ["snowflake"]
    assert default_warehouse().name == "snowflake"


@pytest.mark.parametrize("name", sorted(WAREHOUSES), ids=str)
def test_every_warehouse_registers_a_capability(name: str) -> None:
    cap = CAPABILITIES[name]
    assert set(cap.files) == {"transform/profiles.yml", f"docs/{name}.md"}
    assert cap.warehouse == name


@pytest.mark.parametrize("name", sorted(WAREHOUSES), ids=str)
def test_every_warehouse_has_its_uv_extra(name: str) -> None:
    """The generated README says `uv sync --extra <name>`; this is what keeps
    that sentence true for every entry, including the next one."""
    doc = tomllib.loads((ROOT / "pyproject.toml").read_text())
    extras = doc["project"]["optional-dependencies"]
    assert name in extras, f"pyproject has no `{name}` extra"
    adapter = WAREHOUSES[name].adapter
    assert any(adapter in dep for dep in extras[name]), (
        f"extra `{name}` does not install {adapter}")


@pytest.mark.parametrize("name", sorted(WAREHOUSES), ids=str)
def test_a_warehouse_swaps_prod_and_only_prod(name: str) -> None:
    """The seam's whole safety argument: a capability that could also move
    `dev` is a capability that breaks the laptop build."""
    text = render_profiles("demo", {**PROJECT_TARGETS, "prod": WAREHOUSES[name].output})
    doc = yaml.safe_load(text)["demo"]["outputs"]
    for target in ("dev", "ci", "base"):
        assert doc[target]["type"] == "duckdb"
        assert doc[target]["path"] == "{{ env_var('PF_DUCKDB_PATH') }}"


# ---------------------------------------------------------------- ducklake ----
def test_ducklake_prod_is_a_lakehouse_catalog() -> None:
    text = render_profiles("demo", {**PROJECT_TARGETS, "prod": WAREHOUSES["ducklake"].output})
    prod = yaml.safe_load(text)["demo"]["outputs"]["prod"]
    # Same engine as dev — that is the target's entire portability story —
    # pointed at a `ducklake:` catalog instead of a local file.
    assert prod["type"] == "duckdb"
    assert prod["path"] == "ducklake:{{ env_var('DUCKLAKE_METADATA') }}"
    # Flow-style list, parsed as a real list: the extension must autoload
    # before dbt's first statement touches the catalog.
    assert prod["extensions"] == ["ducklake", "httpfs"]
    # The metadata location is the one credential-shaped requirement.
    assert WAREHOUSES["ducklake"].env == ("DUCKLAKE_METADATA",)
    # dbt-duckdb ships in the dev group already; the extra exists for
    # production installs, not for laptops.
    assert WAREHOUSES["ducklake"].adapter == "dbt-duckdb"


# ---------------------------------------------------------------- iceberg ----
def test_iceberg_prod_is_an_attached_r2_catalog() -> None:
    text = render_profiles("demo", {**PROJECT_TARGETS, "prod": WAREHOUSES["iceberg"].output})
    prod = yaml.safe_load(text)["demo"]["outputs"]["prod"]
    # Same engine as dev — the DuckLake portability story again — but the
    # warehouse is an ATTACHed Iceberg REST catalog, never the local file.
    assert prod["type"] == "duckdb"
    # Bootstrap detects the scaffold placeholder by PF_DUCKDB_PATH; an iceberg
    # prod carrying that path would be silently reverted to the default.
    assert "PF_DUCKDB_PATH" not in str(prod["path"])
    assert prod["extensions"] == ["iceberg", "httpfs"]
    # The nested blocks survive the renderer as real YAML: one catalog secret,
    # one attach whose alias the `database:` key builds into.
    [secret] = prod["secrets"]
    assert secret["type"] == "iceberg"
    [attach] = prod["attach"]
    assert attach["alias"] == "lake"
    assert attach["options"]["type"] == "iceberg"
    assert prod["database"] == "lake"
    assert WAREHOUSES["iceberg"].env == (
        "R2_CATALOG_WAREHOUSE", "R2_CATALOG_ENDPOINT", "R2_CATALOG_TOKEN")
    assert WAREHOUSES["iceberg"].adapter == "dbt-duckdb"


def test_replace_target_round_trips_nested_blocks() -> None:
    """`replace_target` is text-level and indentation-bounded; a nested attach
    block is the first target whose body is deeper than two levels, so this is
    the shape that would break it."""
    from pf.scaffold.generator import replace_target

    text = render_profiles("demo", PROJECT_TARGETS)
    swapped, changed = replace_target(text, "prod", WAREHOUSES["iceberg"].output)
    assert changed
    prod = yaml.safe_load(swapped)["demo"]["outputs"]["prod"]
    assert prod["attach"][0]["options"]["endpoint"] == (
        "{{ env_var('R2_CATALOG_ENDPOINT') }}")
    # The other targets were not touched, and a second replace is a no-op.
    assert yaml.safe_load(swapped)["demo"]["outputs"]["dev"]["type"] == "duckdb"
    _, changed_again = replace_target(swapped, "prod", WAREHOUSES["iceberg"].output)
    assert not changed_again


# ---------------------------------------------------------------- wiring ----
def test_bootstrap_never_takes_a_project_off_ducklake(tmp_path: Path) -> None:
    """The regression that surfaced the moment DuckLake existed: `_dbt_wiring`
    retrofits the scaffold's placeholder prod onto the default warehouse, and
    it used to detect the placeholder by `type == "duckdb"` — which DuckLake
    also is. Switching a project to DuckLake was silently reverted to Snowflake
    by the very next bootstrap. The placeholder is the `PF_DUCKDB_PATH` local
    file, nothing else."""
    from pf.scaffold.bootstrap import _dbt_wiring
    from pf.scaffold.generator import PROJECT_TARGETS

    d = tmp_path / "groups" / "g" / "projects" / "p" / "transform"
    d.mkdir(parents=True)
    (d / "dbt_project.yml").write_text("name: demo\n")

    # A deliberate DuckLake prod survives.
    (d / "profiles.yml").write_text(render_profiles(
        "demo", {**PROJECT_TARGETS, "prod": WAREHOUSES["ducklake"].output}))
    _dbt_wiring(tmp_path, "g", "p")
    prod = yaml.safe_load((d / "profiles.yml").read_text())["demo"]["outputs"]["prod"]
    assert prod["path"].startswith("ducklake:"), "bootstrap reverted DuckLake to the default"

    # The scaffold placeholder is still retrofitted onto the default warehouse.
    (d / "profiles.yml").write_text(render_profiles("demo", PROJECT_TARGETS))
    _dbt_wiring(tmp_path, "g", "p")
    prod = yaml.safe_load((d / "profiles.yml").read_text())["demo"]["outputs"]["prod"]
    assert prod["type"] == "snowflake"


def test_bootstrap_never_takes_a_project_off_iceberg(tmp_path: Path) -> None:
    """Iceberg is `type: duckdb` like the placeholder and DuckLake, but its
    scratch path is not `PF_DUCKDB_PATH` — which is the whole reason the
    placeholder guard keys on that path. This pins it."""
    from pf.scaffold.bootstrap import _dbt_wiring

    d = tmp_path / "groups" / "g" / "projects" / "p" / "transform"
    d.mkdir(parents=True)
    (d / "dbt_project.yml").write_text("name: demo\n")
    (d / "profiles.yml").write_text(render_profiles(
        "demo", {**PROJECT_TARGETS, "prod": WAREHOUSES["iceberg"].output}))
    _dbt_wiring(tmp_path, "g", "p")
    prod = yaml.safe_load((d / "profiles.yml").read_text())["demo"]["outputs"]["prod"]
    assert prod["database"] == "lake", "bootstrap reverted Iceberg to the default"
    assert prod["attach"][0]["options"]["type"] == "iceberg"
