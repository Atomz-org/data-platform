"""One project, one destination — in the cloud as well as on a laptop.

The local arrangement is safe by construction: a DuckDB file lives inside the
project directory, so two sisters cannot share one without somebody typing the
other's path. Every hosted target loses that property, because the thing that
names the destination is an environment variable and an environment variable is
shared by default. `PF_MOTHERDUCK_DB` was the database name outright, and
`SNOWFLAKE_SCHEMA` defaulted to a constant, so an estate that exported its
credentials once — which is the whole point of exporting them — had every
project building into one place.

Nothing about that failure is loud. Both runs succeed, because writing to the
destination you were configured to write to is not an error; the symptom is a
mart whose numbers move when a sister builds. These tests pin the two halves of
the fix, and the third thing they pin is that `dev`, `ci` and `base` stayed
exactly as they were, because a tenant-safe platform nobody can run on a laptop
is not an improvement.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pf.capabilities import CAPABILITIES
from pf.runtime.targets import PROJECT_TOKEN, WAREHOUSES, get
from pf.runtime.warehouse import Warehouse
from pf.scaffold.generator import PROJECT_TARGETS, render

#: Where each engine spells "the namespace this project builds into". BigQuery
#: is the odd one out; ClickHouse calls a database a schema and lands here too.
DESTINATION = {"schema", "dataset"}


def _dbt_render(value: str, env: dict[str, str]) -> str:
    """Render one profile value the way dbt renders profiles.yml.

    dbt's profile context is essentially `env_var` and nothing else, which is
    why a default has to be expressible as its second argument. Reproduced with
    a real Jinja environment rather than a regex so the test is checking the
    same resolution order dbt performs, including "explicit variable wins".
    """
    from jinja2 import Environment

    return Environment(autoescape=False).from_string(value).render(  # noqa: S701 — not HTML
        env_var=lambda name, default=None: env.get(name, default),
    )


@pytest.fixture()
def no_motherduck(monkeypatch: pytest.MonkeyPatch) -> None:
    """A developer's machine, where neither variable is set."""
    monkeypatch.delenv("PF_MOTHERDUCK_DB", raising=False)
    monkeypatch.delenv("PF_MOTHERDUCK_DATABASE", raising=False)


# ------------------------------------------------------------- motherduck ---
def test_motherduck_is_scoped_to_the_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_motherduck: None
) -> None:
    """One exported prefix, two sisters, two databases.

    This is the defect in one assertion: before the fix both DSNs were `md:acme`
    and the second project silently overwrote the first.
    """
    monkeypatch.setenv("PF_MOTHERDUCK_DB", "acme")
    eu = Warehouse.for_project(tmp_path, "acme", "acme-eu")
    us = Warehouse.for_project(tmp_path, "acme", "acme-us")

    assert eu.dsn == "md:acme_acme_eu"
    assert us.dsn == "md:acme_acme_us"
    assert eu.dsn != us.dsn


def test_an_exact_motherduck_database_is_still_possible(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_motherduck: None
) -> None:
    """Sharing one database remains available — by name, and only by name.

    A migration or a genuinely single-tenant deployment wants an exact database,
    so the escape hatch stays. It beats the prefix, and it is a variable nobody
    already has exported, which is the difference between opting in and
    inheriting.
    """
    monkeypatch.setenv("PF_MOTHERDUCK_DB", "acme")
    monkeypatch.setenv("PF_MOTHERDUCK_DATABASE", "acme_migration")

    assert Warehouse.for_project(tmp_path, "acme", "acme-eu").dsn == "md:acme_migration"
    assert Warehouse.for_project(tmp_path, "acme", "acme-us").dsn == "md:acme_migration"


def test_without_the_variable_the_warehouse_is_the_local_file(
    tmp_path: Path, no_motherduck: None
) -> None:
    """`pf seed` on a laptop: no credentials, no cloud, one file per project."""
    wh = Warehouse.for_project(tmp_path, "acme", "acme-eu")

    assert wh.motherduck is None
    assert wh.dsn == str(tmp_path / "data" / "acme_eu.duckdb")
    assert wh.writer_pool == "duckdb_writer_acme_eu"


# ---------------------------------------------------------- prod targets ----
def test_every_production_destination_carries_the_tenant() -> None:
    """Exactly one key per warehouse is tenant-scoped, and it is the destination.

    Asserted over the registry rather than per engine so that adding ClickHouse
    — or the next one — cannot land a shared default by being written before
    anybody re-read this file.
    """
    for name, wh in WAREHOUSES.items():
        scoped = [k for k, v in wh.output.items()
                  if isinstance(v, str) and PROJECT_TOKEN in v]
        assert scoped and set(scoped) <= DESTINATION, f"{name}: {scoped}"
        assert len(scoped) == 1, f"{name} scopes more than its destination: {scoped}"


def test_prod_schema_defaults_to_the_project() -> None:
    """With nothing exported, each project resolves to its own namespace."""
    snowflake = get("snowflake")
    eu = _dbt_render(snowflake.output_for("acme-eu")["schema"], {})
    us = _dbt_render(snowflake.output_for("acme-us")["schema"], {})
    assert (eu, us) == ("ANALYTICS_acme_eu", "ANALYTICS_acme_us")

    bigquery = get("bigquery")
    assert _dbt_render(bigquery.output_for("acme-eu")["dataset"], {}) == "analytics_acme_eu"
    assert _dbt_render(bigquery.output_for("acme-us")["dataset"], {}) == "analytics_acme_us"


def test_an_explicit_schema_env_var_still_wins() -> None:
    """An estate that has already carved up its schemas is not overruled.

    The default changed; the override did not. These are still two-argument
    `env_var` calls, so a set variable is what dbt uses.
    """
    schema = get("snowflake").output_for("acme-eu")["schema"]
    assert _dbt_render(schema, {"SNOWFLAKE_SCHEMA": "MARTS"}) == "MARTS"

    dataset = get("bigquery").output_for("acme-eu")["dataset"]
    assert _dbt_render(dataset, {"BIGQUERY_DATASET": "reporting"}) == "reporting"


def test_credentials_are_left_shared() -> None:
    """Who connects is an estate-wide fact; where it lands is not.

    Account, user and password are legitimately one set for a whole estate.
    Scoping them per project would be a different — and much louder — bug, so
    every key but the destination resolves identically for two sisters.
    """
    for name, wh in WAREHOUSES.items():
        eu, us = wh.output_for("acme-eu"), wh.output_for("acme-us")
        expected_shared = set(wh.output) - DESTINATION
        assert {k for k in wh.output if eu[k] == us[k]} == expected_shared, name
        for key in expected_shared:
            assert eu[key] == wh.output[key], f"{name}.{key} changed without a tenant"


def test_resolution_leaves_non_string_values_alone() -> None:
    """`threads: 8` and `secure: True` must stay typed.

    `render_target` renders a bool as `true` and an int bare; a value
    stringified on the way through would reach the YAML as `"True"`, which is
    valid, wrong, and the kind of thing nobody can copy an idiom from.
    """
    assert get("snowflake").output_for("acme-eu")["threads"] == 8
    assert get("clickhouse").output_for("acme-eu")["secure"] is True


# ------------------------------------------------------------- rendering ----
def test_the_generated_profile_resolves_the_token() -> None:
    """End to end: the token is the scaffolder's, and the scaffolder resolves it.

    `warehouse_capability` writes `transform/profiles.yml` through
    `pf.scaffold.generator.render`, so what reaches a project is a schema name.
    A brace surviving to disk would be a dbt-side literal and a broken build.
    """
    text = render(CAPABILITIES["snowflake"].files["transform/profiles.yml"],
                  {"group": "acme", "project": "acme-eu", "module": "acme_eu"})

    assert "ANALYTICS_acme_eu" in text
    assert PROJECT_TOKEN not in text
    # The env_var calls themselves must survive — they are what keeps a
    # credential out of a committed file.
    assert "{{ env_var('SNOWFLAKE_ACCOUNT') }}" in text


def test_the_duckdb_targets_are_untouched() -> None:
    """`dev`, `ci` and `base` are the laptop build and carry no tenant token.

    They do not need one: `PF_DUCKDB_PATH` already points at a file inside the
    project. A token here would be one that nothing resolves on the paths that
    write these targets by hand.
    """
    for name, spec in PROJECT_TARGETS.items():
        assert spec["type"] == "duckdb", name
        assert PROJECT_TOKEN not in str(spec), name

    text = render(CAPABILITIES["snowflake"].files["transform/profiles.yml"],
                  {"group": "acme", "project": "acme-eu", "module": "acme_eu"})
    assert text.count("type: duckdb") == 3  # dev, ci, base — prod is snowflake
    assert "schema: base" in text


def test_no_tenant_token_reaches_the_catalogue() -> None:
    """OpenMetadata's connection is dumped straight to YAML with no render pass.

    So the token stops at the dbt output block. If a warehouse ever needs a
    tenant-scoped catalogue connection it has to be resolved where that file is
    written, not declared here and hoped for.
    """
    for name, wh in WAREHOUSES.items():
        assert PROJECT_TOKEN not in str(wh.om_connection), name
