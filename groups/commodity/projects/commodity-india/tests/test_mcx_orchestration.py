"""The MCX job graph: every commodity job is the whole pipeline, rerunnable on
its own, and the catalogue follows it without being able to fail it."""

from __future__ import annotations

import pytest
from commodity_india.defs import mcx
from dagster import AssetKey, DagsterInstance


@pytest.fixture(scope="module")
def defs():
    return mcx.mcx_definitions()


def test_every_commodity_job_runs_the_whole_pipeline_and_not_the_catalogue(defs) -> None:
    """dlt → landed tables → dbt → semantic check → Evidence (audited) → Wren,
    for that commodity only. The catalogue talks to a server: it is never in a
    data job, so a catalogue outage cannot fail a day's market data."""
    from commodity_india.definitions import defs as full

    for commodity in mcx.job_settings():
        keys = set(full.resolve_job_def(f"mcx_{commodity}_ingest").asset_layer.executable_asset_keys)
        assert mcx.commodity_key(commodity) in keys
        others = {mcx.commodity_key(c) for c in mcx.job_settings()} - {mcx.commodity_key(commodity)}
        assert not keys & others, "a commodity's job loads that commodity only"
        for part in ("mcx_semantic_layer", "mcx_report_site", "wren_semantic_layer", "fct_mcx_commodity_daily"):
            assert AssetKey([mcx.PREFIX, part]) in keys, (commodity, part)
        assert not keys & {mcx.SYNC_KEY, mcx.CATALOG_KEY}


def test_the_catalogue_has_its_own_job_and_a_sensor_that_follows_every_mcx_job(defs) -> None:
    from commodity_india.definitions import defs as full

    keys = set(full.resolve_job_def(mcx.CATALOG_JOB).asset_layer.executable_asset_keys)
    assert keys == {mcx.SYNC_KEY, mcx.CATALOG_KEY}
    (sensor,) = [s for s in defs.sensors if s.name == "mcx_catalog_after_run"]
    watched = {j.name for j in sensor._monitored_jobs}  # noqa: SLF001 — no public accessor
    assert watched == {f"mcx_{c}_ingest" for c in mcx.job_settings()} | {mcx.TRANSFORM_JOB, mcx.ALL_JOB}


def test_the_bulk_job_loads_every_commodity_then_runs_the_pipeline_once() -> None:
    from commodity_india.definitions import defs as full

    keys = set(full.resolve_job_def(mcx.ALL_JOB).asset_layer.executable_asset_keys)
    assert {mcx.commodity_key(c) for c in mcx.job_settings()} <= keys
    assert AssetKey([mcx.PREFIX, "mcx_report_site"]) in keys and not keys & {mcx.SYNC_KEY, mcx.CATALOG_KEY}


def test_the_site_waits_for_the_semantic_check_and_the_writer_pool(defs) -> None:
    by_key = {k: a for a in defs.assets for k in a.keys}
    site = by_key[AssetKey([mcx.PREFIX, "mcx_report_site"])]
    assert AssetKey([mcx.PREFIX, "mcx_semantic_layer"]) in site.dependency_keys
    for name in ("mcx_semantic_layer", "mcx_report_site"):
        pool = by_key[AssetKey([mcx.PREFIX, name])].op.pool
        assert pool and pool.startswith("duckdb_writer_"), name


def test_semantic_rows_reads_metricflow_output() -> None:
    out = """✔ Success 🦄 - query completed after 0.09 seconds
mcx_session__mcx_commodity      mcx_session_days    mcx_turnover_inr    mcx_contango_share
----------------------------  ------------------  ------------------  --------------------
gold                                        6297         1.64445e+14              0.924726
silver                                      5100         9.1e+13                  0.9865
"""
    rows = mcx.semantic_rows(out, "mcx_session__mcx_commodity")
    assert rows == {"gold": ["6297", "1.64445e+14", "0.924726"], "silver": ["5100", "9.1e+13", "0.9865"]}
    assert mcx.semantic_rows("no table here", "mcx_session__mcx_commodity") == {}


def test_the_catalogue_follows_a_run_only_with_a_credential_and_coalesces() -> None:
    from commodity_india.definitions import defs as full
    from dagster import RunRequest, SkipReason

    instance = DagsterInstance.ephemeral()
    run = instance.create_run_for_job(full.resolve_job_def("mcx_gold_ingest"), tags={"mcx/commodity": "gold"})
    skipped = mcx.catalog_request(run, instance, env={})
    assert isinstance(skipped, SkipReason) and "not set" in skipped.skip_message
    request = mcx.catalog_request(run, instance, env={mcx.TOKEN_ENV: "x"})
    assert isinstance(request, RunRequest)
    assert request.run_key == f"after-{run.run_id}" and request.tags["mcx/commodity"] == "gold"
    # A catalogue run still waiting will read this run's state: no second one.
    instance.create_run_for_job(full.resolve_job_def(mcx.CATALOG_JOB))
    assert isinstance(mcx.catalog_request(run, instance, env={mcx.TOKEN_ENV: "x"}), SkipReason)
