"""DuckLake as a production target, and the MCP seam warehouses arrive through.

The properties worth pinning down are the ones that would fail quietly. A nested
`attach:` that renders as a Python repr still *looks* like a profiles.yml until
dbt reads it; an MCP block written wholesale takes a project's hand-added servers
with it; and a read-write default on a production lake is one tool call away from
a dropped table.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from pf.capabilities import CAPABILITIES
from pf.capabilities import apply as apply_capability
from pf.runtime.targets import WAREHOUSES
from pf.scaffold.generator import PROJECT_TARGETS, render_profiles, render_target


# ------------------------------------------------------------- the renderer --
def test_nested_values_render_as_parseable_yaml() -> None:
    """The repr of a list is not a YAML contract — see `_yaml_flow`."""
    text = render_target("prod", {
        "type": "duckdb",
        "extensions": ["ducklake", "httpfs"],
        "attach": [{"path": "ducklake:cat.ducklake", "alias": "lake"}],
    })
    parsed = yaml.safe_load(text)["prod"]
    assert parsed["extensions"] == ["ducklake", "httpfs"]
    assert parsed["attach"] == [{"path": "ducklake:cat.ducklake", "alias": "lake"}]


def test_a_colon_in_a_nested_value_survives() -> None:
    """`ducklake:x` is a mapping to a YAML parser unless the scalar is quoted."""
    text = render_target("prod", {"attach": [{"path": "ducklake:postgres:dbname=lake"}]})
    assert yaml.safe_load(text)["prod"]["attach"][0]["path"] == (
        "ducklake:postgres:dbname=lake")


def test_flat_targets_are_rendered_exactly_as_before() -> None:
    """The nested branch must not touch the shape every other warehouse uses."""
    text = render_target("dev", {"type": "duckdb", "threads": 4, "secure": True})
    assert text == '    dev:\n      type: duckdb\n      threads: 4\n      secure: true\n'


# ---------------------------------------------------------------- ducklake --
def test_ducklake_profile_round_trips() -> None:
    wh = WAREHOUSES["ducklake"]
    text = render_profiles("demo", {**PROJECT_TARGETS, "prod": wh.output})
    prod = yaml.safe_load(text)["demo"]["outputs"]["prod"]

    # DuckLake is DuckDB with a catalog attached, not its own adapter.
    assert prod["type"] == "duckdb"
    assert wh.adapter == "dbt-duckdb"
    assert prod["attach"][0]["path"] == "{{ env_var('DUCKLAKE_CATALOG') }}"
    assert "ducklake" in prod["extensions"]


def test_ducklake_does_not_become_the_default_warehouse() -> None:
    """Exactly one warehouse is default-enabled, and it is not this one."""
    defaults = [n for n, w in WAREHOUSES.items() if w.default_enabled]
    assert defaults == ["snowflake"]


def test_ducklake_leaves_the_dev_targets_alone() -> None:
    """A warehouse may only change `prod` — the seam that protects the laptop."""
    wh = WAREHOUSES["ducklake"]
    rendered = yaml.safe_load(
        render_profiles("demo", {**PROJECT_TARGETS, "prod": wh.output}))
    outputs = rendered["demo"]["outputs"]
    for name in ("dev", "ci", "base"):
        assert outputs[name]["path"] == "{{ env_var('PF_DUCKDB_PATH') }}"


# --------------------------------------------------------------- the seam ---
@pytest.mark.parametrize("name", ["snowflake", "bigquery", "ducklake"])
def test_warehouse_mcp_reaches_its_capability(name: str) -> None:
    assert WAREHOUSES[name].mcp, f"{name} declares no MCP server"
    assert CAPABILITIES[name].mcp == dict(WAREHOUSES[name].mcp)


def test_mcp_credentials_are_not_dbt_credentials() -> None:
    """`env` gates `DBT_TARGET=prod`; a missing MCP token must not read as broken."""
    for name in ("snowflake", "bigquery", "ducklake"):
        env = WAREHOUSES[name].env
        assert not any("MCP" in v for v in env), f"{name} put an MCP var in env"


def test_ducklake_mcp_is_read_only() -> None:
    """Production. `--read-write` is one tool call from a dropped table."""
    args = WAREHOUSES["ducklake"].mcp["ducklake"]["args"]
    assert "--read-write" not in args


def test_ducklake_mcp_and_dbt_read_the_same_catalog() -> None:
    """Two definitions of "which lake" is how they end up disagreeing."""
    wh = WAREHOUSES["ducklake"]
    assert "DUCKLAKE_CATALOG" in wh.mcp["ducklake"]["args"][-1]
    assert "DUCKLAKE_CATALOG" in str(wh.output["attach"])


# ------------------------------------------------------------- .mcp.json ----
def test_apply_creates_mcp_json_when_absent(tmp_path: Path) -> None:
    apply_capability(CAPABILITIES["ducklake"], tmp_path, tmp_path,
                     {"group": "g", "project": "p", "module": "p"})
    written = json.loads((tmp_path / ".mcp.json").read_text())
    assert "ducklake" in written["mcpServers"]


def test_apply_merges_rather_than_clobbers(tmp_path: Path) -> None:
    """The failure this merge exists to prevent: someone else's server, deleted."""
    (tmp_path / ".mcp.json").write_text(json.dumps(
        {"mcpServers": {"pf": {"command": "uv", "args": ["run", "pf", "mcp"]}}}))

    apply_capability(CAPABILITIES["bigquery"], tmp_path, tmp_path,
                     {"group": "g", "project": "p", "module": "p"})

    servers = json.loads((tmp_path / ".mcp.json").read_text())["mcpServers"]
    assert set(servers) == {"pf", "bigquery"}
    assert servers["pf"]["args"] == ["run", "pf", "mcp"]


def test_a_capability_without_mcp_writes_no_file(tmp_path: Path) -> None:
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.json").write_text("{}")
    apply_capability(CAPABILITIES["github"], tmp_path, tmp_path,
                     {"group": "g", "project": "p", "module": "p"})
    assert not (tmp_path / ".mcp.json").exists()
