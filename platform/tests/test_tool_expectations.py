"""dbt-expectations tool: declaration, generation, and the managed directory.

The generation contract is the one to pin: every emitted file must be valid
Jinja calling the package's real test macros, regeneration must delete only
what it generated, and a project with no graph must still get the package —
the floor degrades, the vocabulary does not.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pf.tools import expectations as ex
from pf.tools import registry

DBT_PROJECT = """\
name: 'demo'
version: '1.0.0'
config-version: 2
profile: 'demo'
"""


def _project(tmp_path: Path) -> Path:
    d = tmp_path / "groups" / "g" / "projects" / "p"
    t = d / "transform"
    t.mkdir(parents=True)
    (t / "dbt_project.yml").write_text(DBT_PROJECT)
    return d


def _marts(*models: ex.MartModel):
    def fake(_project_dir: Path) -> list[ex.MartModel]:
        return list(models)
    return fake


# --------------------------------------------------------------- generate --
def test_generated_sql_calls_the_real_macros(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(ex, "_annotated_marts", _marts(
        ex.MartModel(name="fct_orders", grain="one order", key="order_id")))
    files = ex.generate_tests(_project(tmp_path))

    assert set(files) == {
        "fct_orders__not_empty.sql",
        "fct_orders__order_id__unique.sql",
        "fct_orders__order_id__not_null.sql",
    }
    body = files["fct_orders__not_empty.sql"]
    # The double braces must have survived every formatting layer: this is
    # Jinja for dbt, and `{ config(` is a file that fails to parse.
    assert "{{ config(tags=['expectations']) }}" in body
    assert ("{{ dbt_expectations.test_expect_table_row_count_to_be_between(\n"
            "    ref('fct_orders'), min_value=1) }}") in body
    assert body.startswith(ex.MARKER)

    unique = files["fct_orders__order_id__unique.sql"]
    assert ("{{ dbt_expectations.test_expect_column_values_to_be_unique(\n"
            "    ref('fct_orders'), 'order_id') }}") in unique


def test_a_mart_without_a_safe_key_gets_only_the_row_count_floor(
        tmp_path: Path, monkeypatch) -> None:
    """Aggregate marts have no surrogate key; PII keys are excluded upstream.
    Either way the model still gets its not-empty floor and nothing invented."""
    monkeypatch.setattr(ex, "_annotated_marts", _marts(
        ex.MartModel(name="agg_daily", grain="one day", key="")))
    files = ex.generate_tests(_project(tmp_path))
    assert set(files) == {"agg_daily__not_empty.sql"}


# ------------------------------------------------------------ managed dir --
def test_regeneration_removes_stale_and_spares_hand_written(
        tmp_path: Path, monkeypatch) -> None:
    d = _project(tmp_path)
    monkeypatch.setattr(ex, "_annotated_marts", _marts(
        ex.MartModel(name="fct_orders", grain="", key="")))
    ex.write_tests(d)

    tdir = ex.tests_dir(d)
    # A previously generated test whose model has since gone...
    (tdir / "fct_gone__not_empty.sql").write_text(ex.MARKER + "\nselect 1")
    # ...and a hand-written singular test that strayed into the directory.
    (tdir / "mine.sql").write_text("select broken_id from x where broken_id is null")

    written, unchanged, removed = ex.write_tests(d)
    assert (written, unchanged, removed) == (0, 1, 1)
    assert not (tdir / "fct_gone__not_empty.sql").exists()
    assert (tdir / "mine.sql").exists()


def test_write_is_idempotent(tmp_path: Path, monkeypatch) -> None:
    d = _project(tmp_path)
    monkeypatch.setattr(ex, "_annotated_marts", _marts(
        ex.MartModel(name="fct_orders", grain="", key="k")))
    assert ex.write_tests(d) == (3, 0, 0)
    assert ex.write_tests(d) == (0, 3, 0)


# --------------------------------------------------------------- bootstrap --
def test_bootstrap_without_a_graph_still_declares_the_package(tmp_path: Path) -> None:
    d = _project(tmp_path)
    r = ex.bootstrap_project(tmp_path, "g", "p", d, {})
    assert r.status == "ok"
    assert "floor not generated" in r.detail

    pkgs = yaml.safe_load((d / "transform" / "packages.yml").read_text())
    assert any(e["package"] == ex.PACKAGE for e in pkgs["packages"])
    # No graph, no generated directory — an empty managed dir would read as
    # "generated and found nothing", which is not what happened.
    assert not ex.tests_dir(d).exists()


def test_bootstrap_skips_a_project_with_no_dbt(tmp_path: Path) -> None:
    d = tmp_path / "groups" / "g" / "projects" / "empty"
    d.mkdir(parents=True)
    assert ex.bootstrap_project(tmp_path, "g", "empty", d, {}).status == "skipped"


# ---------------------------------------------------------------- registry --
def test_registered_offline_default_enabled_and_gate_safe() -> None:
    tools = registry.all_tools()
    assert "expectations" in tools
    t = tools["expectations"]
    assert t.offline and t.default_enabled
    assert t.supports("group") and t.supports("project")
    # Generated from the ontology: edits are a fork, so the gate reports them.
    assert t.gate_sections() == {
        "impact_required": ["**/transform/tests/expectations/**"]}
    # Deliberately no dagster hook — the tests run inside the project's own
    # dbt assets, and a second runner would be a second verdict.
    assert t.dagster == ""
