"""MCX orchestration: one job per commodity, then dbt, then Evidence.

    mcx_<commodity>_daily    schedule    one per commodity, staggered, pausable any time
    mcx_<commodity>_ingest   job ─┬─ commodity_india/mcx_<commodity>   dlt, that commodity only
                                  ├─ mcx_landed_tables (3 raw tables)   verify what landed
                                  ├─ stg_mcx__* → int_mcx__* → fct/dim/rpt_mcx_*   dbt build + tests
                                  ├─ mcx_semantic_layer                 MetricFlow answers for it
                                  ├─ mcx_report_site                    evidence build + format audit
                                  ├─ okf · wren_semantic_layer          knowledge bundle · Wren check
    mcx_transform_and_report job     the dbt + Evidence half alone, for a model or page change
    mcx_all_ingest           job         every commodity's load, then one dbt → metrics → Evidence
                                         → Wren pass: the bulk run (backfill, a missed morning)
    mcx_catalog_publish      job ─┬─ catalog_sync                        graph, MDL, OpenMetadata tables
                                  └─ mcx_catalog                         MCX glossary, tiers, lineage
    mcx_catalog_after_run    sensor      launches the catalog job after any MCX job succeeds

**Rerun any commodity at any time.** Launch `mcx_<commodity>_ingest` (UI:
Jobs → Launch; CLI: `dagster job launch`). Every step is idempotent — dlt merges
on the natural key and resumes from each contract's cursor (re-reading the last
`refetch_days`), dbt rebuilds the MCX models, the site and the Wren workspace
check are rebuilt from the warehouse — so a rerun of a day, a week or a whole
history converges on the same tables. Two commodities rerun at once queue on
the warehouse's writer pool (limit 1, op granularity) rather than colliding.

**One commodity, one asset — an asset factory.** `_commodity_asset(c)` builds
`commodity_india/mcx_<c>` for every commodity in the `mcx_products` seed, so a
failed zinc load is a red zinc asset and nothing else, and each commodity has
its own materialization history. The three raw tables stay one set of keys —
what the dbt sources resolve to (`_translator` in the factory) — produced by
one `mcx_landed_tables` step that every commodity asset feeds and that verifies
what landed, so lineage reads commodity → tables → staging → marts → report
inside each job. Not partitions: incremental state is per contract
in dlt, and the factory's `commodity_india_all` job selects `*`, where a
partitioned asset would make it demand a partition key.

**The job is the whole pipeline.** Each commodity's job selects its dlt asset
and everything downstream of the MCX tables, so the run graph shows dlt → dbt →
Evidence and a failure lands on the step that failed. dbt runs the MCX subset
only (`dagster-dbt` passes the selection as `--select`), so a commodity's job
rebuilds MCX, not the project. Every step writes or reads one DuckDB file, so
the jobs queue on its writer pool; the schedules start 3 minutes apart
(`staggered`) to keep that queue short.

Assets here take `pool=wh.writer_pool`, like every writer the factory builds:
the dlt load, and the Evidence build, which reads the warehouse and must not
open it mid-write.
"""

import os
import subprocess
from pathlib import Path

import yaml
from dagster import (
    AssetExecutionContext,
    AssetKey,
    AssetSelection,
    AssetSpec,
    DefaultScheduleStatus,
    DefaultSensorStatus,
    Definitions,
    MaterializeResult,
    MetadataValue,
    ScheduleDefinition,
    asset,
    define_asset_job,
    multi_asset,
)
from pf.runtime.warehouse import Warehouse

from commodity_india import mcx_feed
from commodity_india.sources import mcx

GROUP = "commodity"
PROJECT = "commodity-india"
PROJECT_DIR = Path(__file__).resolve().parents[3]
PREFIX = PROJECT.replace("-", "_")
JOBS_FILE = Path(__file__).with_name("mcx_jobs.yaml")
REPORTING_DIR = PROJECT_DIR / "reporting"

TABLES = ("contract_master", "futures_bhavcopy", "options_bhavcopy")
INGEST_KEYS = [AssetKey([PREFIX, t]) for t in TABLES]
TRANSFORM_JOB = "mcx_transform_and_report"
ALL_JOB = "mcx_all_ingest"

#: The marts the report pages read; the Evidence build waits on them.
REPORT_MODELS = ("rpt_mcx_commodity_board", "fct_mcx_commodity_daily",
                 "fct_mcx_options_daily", "fct_mcx_futures_daily", "dim_mcx_contracts")


def job_settings(path: Path = JOBS_FILE) -> dict[str, dict[str, str]]:
    """Per-commodity cron and initial schedule state: seed ∪ yaml, yaml wins.

    Raises on a yaml commodity the seed does not know, or a schedule state that
    is not `running`/`stopped` — a typo there would otherwise leave a commodity
    running on defaults while its owner believes it is paused.
    """
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    doc = doc or {}
    defaults = {"cron": "30 6 * * 2-6", "schedule": "running", **(doc.get("defaults") or {})}
    overrides = doc.get("commodities") or {}
    known = mcx_feed.commodities()
    if unknown := sorted(set(overrides) - set(known)):
        raise KeyError(f"{path.name}: not an mcx_commodity in mcx_products.csv: {', '.join(unknown)}")
    out: dict[str, dict[str, str]] = {}
    for commodity in known:
        s = {**defaults, **(overrides.get(commodity) or {})}
        if s["schedule"] not in ("running", "stopped"):
            raise ValueError(f"{path.name}: {commodity}.schedule must be running or stopped, "
                             f"not {s['schedule']!r}")
        out[commodity] = {"cron": str(s["cron"]), "schedule": str(s["schedule"])}
    return out


def commodity_key(commodity: str) -> AssetKey:
    return AssetKey([PREFIX, f"mcx_{commodity}"])


def _commodity_asset(wh: Warehouse, commodity: str):
    """The factory: one software-defined asset per MCX commodity."""
    codes = ", ".join(mcx_feed.codes_for(commodity))

    @asset(
        name=f"mcx_{commodity}",
        key_prefix=[PREFIX],
        group_name="ingest_mcx",
        pool=wh.writer_pool,
        kinds={"dlt"},
        tags={"mcx": "", "mcx/commodity": commodity},
        description=f"MCX {commodity} ({codes}): futures and options bhavcopy and the contract "
                    f"list, through the `{mcx.pipeline_name(commodity)}` dlt pipeline into the "
                    "`mcx` dataset. Resumes from its last committed batch.",
        metadata={"source": "mcx", "dataset": mcx.DATASET, "commodity": commodity,
                  "module": "commodity_india.sources.mcx", "dagster/kind": "dlt"},
    )
    def _load(context: AssetExecutionContext) -> MaterializeResult:
        summary = mcx.load_commodity(
            wh, commodity,
            on_batch=lambda n, pending, _info: context.log.info(
                f"mcx {commodity}: batch {n} committed, {pending} contract(s) pending"))
        return MaterializeResult(metadata={
            "commodities": MetadataValue.json([commodity]),
            "batches": summary["batches"],
            "loads": len(summary["load_ids"]),
            "pipeline": summary["pipeline"] or "",
            "rows_in_dataset": MetadataValue.json(summary["rows"]),
        })

    return _load


def _landed_tables_asset(wh: Warehouse, commodities: list[str]):
    """The three raw tables as one executable step: *verify what landed*.

    Declared-only specs would be truer to how the rows get there (a commodity
    asset's dlt pipeline writes them), but Dagster leaves non-executable assets
    out of a job, so the job graph showed the load with nothing after it. As a
    step, the tables sit where they belong — load → tables → staging — and do a
    job worth doing: read back what the commodity put in `mcx`, record rows and
    the latest session per table, and fail the run when a commodity landed
    nothing, before dbt builds marts over an empty load.

    In a commodity's own job the commodity comes from the run's `mcx/commodity`
    tag. Run anywhere else (the rebuild job, `commodity_india_all`) it checks the
    tables as a whole.
    """
    specs = [
        AssetSpec(key, group_name="ingest_mcx", deps=[commodity_key(c) for c in commodities],
                  kinds={"duckdb"}, tags={"mcx": ""},
                  description=f"`mcx.{table}` — every MCX commodity's rows, merged on key; written "
                              "by the mcx_<commodity> dlt pipelines, verified here, read by stg_mcx__*.",
                  metadata={"source": "mcx", "dataset": mcx.DATASET})
        for key, table in zip(INGEST_KEYS, TABLES, strict=True)
    ]

    @multi_asset(name="mcx_landed_tables", specs=specs, pool=wh.writer_pool)
    def mcx_landed_tables(context: AssetExecutionContext):
        commodity = context.run.tags.get("mcx/commodity")
        where = "where mcx_commodity = ?" if commodity else ""
        params = [commodity] if commodity else []
        with wh.connect(read_only=True) as con:
            stats = {}
            for table in TABLES:
                day_col = "expiry_date" if table == "contract_master" else "trade_date"
                rows, latest = con.execute(
                    f"select count(*), max({day_col}) from {mcx.DATASET}.{table} {where}",
                    params).fetchone()
                stats[table] = (rows, latest)
        if not stats["futures_bhavcopy"][0]:
            scope = f"commodity {commodity!r}" if commodity else "any commodity"
            raise RuntimeError(f"mcx.futures_bhavcopy has no rows for {scope} — "
                               "the load landed nothing; not building marts over it")
        for key, table in zip(INGEST_KEYS, TABLES, strict=True):
            rows, latest = stats[table]
            yield MaterializeResult(asset_key=key, metadata={
                "scope": commodity or "all commodities",
                "rows": rows,
                "latest": str(latest) if latest else "",
            })

    return mcx_landed_tables


#: Metrics that prove each MCX semantic model answers for a commodity: one per
#: contract-code model, one per commodity model. `--where` scopes them to the
#: run's commodity, so a gold run proves gold, not the table as a whole.
SEMANTIC_CHECKS = (
    (("mcx_session_days", "mcx_contango_share", "mcx_turnover_inr"), "mcx_session__mcx_commodity"),
    (("mcx_commodity_sessions", "mcx_commodity_avg_daily_return"), "mcx_commodity_day__mcx_commodity"),
)
SEMANTIC_MODELS = ("fct_mcx_commodity_daily", "fct_mcx_commodity_rollup_daily")


def _semantic_layer_asset(wh: Warehouse, commodities: list[str]):
    @asset(
        name="mcx_semantic_layer",
        key_prefix=[PREFIX],
        group_name="semantic",
        pool=wh.writer_pool,   # MetricFlow opens the warehouse; never beside a writer
        deps=[AssetKey([PREFIX, m]) for m in SEMANTIC_MODELS],
        kinds={"metricflow"},
        tags={"mcx": ""},
        description="The governed metrics answer for what was just built: MetricFlow queries "
                    "each MCX semantic model, scoped to the run's commodity (all when unscoped).",
    )
    def mcx_semantic_layer(context: AssetExecutionContext) -> MaterializeResult:
        from pf.runtime.dbt_runtime import mf_query

        commodity = context.run.tags.get("mcx/commodity")
        wanted = [commodity] if commodity else commodities
        answered: dict[str, dict[str, str]] = {}
        for metrics, dim in SEMANTIC_CHECKS:
            where = f"{{{{ Dimension('{dim}') }}}} = '{commodity}'" if commodity else ""
            proc = mf_query(PROJECT_DIR, list(metrics), [dim], where=where, limit=100)
            rows = semantic_rows(proc.stdout or "", dim)
            if proc.returncode != 0 or not rows:
                raise RuntimeError(f"MetricFlow did not answer {', '.join(metrics)} by {dim}"
                                   f" for {commodity or 'any commodity'}:\n{(proc.stdout + proc.stderr)[-1500:]}")
            missing = sorted(set(wanted) - set(rows)) if commodity else []
            if missing:
                raise RuntimeError(f"MetricFlow has no {metrics[0]} for {missing} — the marts hold no "
                                   "session for it")
            for name, values in rows.items():
                answered.setdefault(name, {}).update(dict(zip(metrics, values, strict=False)))
        return MaterializeResult(metadata={
            "scope": commodity or "all commodities",
            "commodities_answered": len(answered),
            "answers": MetadataValue.json({k: answered[k] for k in sorted(answered)[:20]}),
        })

    return mcx_semantic_layer


def semantic_rows(stdout: str, dim: str) -> dict[str, list[str]]:
    """MetricFlow's table output as {group value: [metric values...]}."""
    lines = stdout.splitlines()
    head = next((i for i, line in enumerate(lines) if line.split()[:1] == [dim]), None)
    if head is None:
        return {}
    out: dict[str, list[str]] = {}
    for line in lines[head + 2:]:
        cells = line.split()
        if not cells:
            break
        out[cells[0]] = cells[1:]
    return out


def _report_site_asset(wh: Warehouse, semantic_key: AssetKey):
    @asset(
        name="mcx_report_site",
        key_prefix=[PREFIX],
        group_name="reporting",
        pool=wh.writer_pool,
        deps=[AssetKey([PREFIX, m]) for m in REPORT_MODELS] + [AssetKey([PREFIX, "reporting"]), semantic_key],
        kinds={"evidence"},
        tags={"mcx": ""},
        description="Evidence site build: `npm run sources` extracts the marts, `npm run build` "
                    "renders the MCX summary and one page per commodity to reporting/build, then "
                    "`pf report audit` fails the step on any format error — declared (fmt-unit, "
                    "fmt-missing) or rendered (fmt-rendered: NaN, undefined, raw floats).",
    )
    def mcx_report_site(context: AssetExecutionContext) -> MaterializeResult:
        from pf.projections.report_audit import audit

        if not (REPORTING_DIR / "node_modules").is_dir():
            context.log.warning("reporting/node_modules missing — run `npm install` in reporting/")
            return MaterializeResult(metadata={"built": False, "reason": "npm install not run"})
        env = {**os.environ, "PF_DUCKDB_PATH": str(wh.path)}
        for step in (["npm", "run", "sources"], ["npm", "run", "build"]):
            proc = subprocess.run(step, cwd=REPORTING_DIR, env=env, capture_output=True,
                                  text=True, timeout=1800, check=False)
            if proc.returncode != 0:
                raise RuntimeError(f"{' '.join(step)} failed:\n{(proc.stdout + proc.stderr)[-3000:]}")
            context.log.info(f"{' '.join(step)} ok")
        score, findings = audit(PROJECT_DIR)
        errors = [f for f in findings if f.severity == "error"]
        for f in findings:
            if f.severity != "info":
                context.log.warning(str(f))
        if errors:
            raise RuntimeError(f"the report fails its format audit ({len(errors)} error(s)):\n"
                               + "\n".join(str(f) for f in errors[:20]))
        pages = sorted(str(p.relative_to(REPORTING_DIR / "build"))
                       for p in (REPORTING_DIR / "build" / "mcx").rglob("index.html"))
        return MaterializeResult(metadata={
            "built": True, "mcx_pages": MetadataValue.json(pages),
            "audit_score": score,
            "audit_warnings": sum(1 for f in findings if f.severity == "warning"),
            "path": MetadataValue.path(str(REPORTING_DIR / "build")),
        })

    return mcx_report_site


CATALOG_JOB = "mcx_catalog_publish"
CATALOG_KEY = AssetKey([PREFIX, "mcx_catalog"])
SYNC_KEY = AssetKey([PREFIX, "catalog_sync"])
TOKEN_ENV = "OPENMETADATA_JWT_TOKEN"


def _load_ontology_module():
    """catalog/mcx_ontology.py, loaded by path: it is a standalone script
    (standard library only, runnable with plain `python`), not a package."""
    import importlib.util

    path = PROJECT_DIR / "catalog" / "mcx_ontology.py"
    spec = importlib.util.spec_from_file_location("commodity_india_mcx_ontology", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def _catalog_asset(site_key: AssetKey):
    @asset(
        name="mcx_catalog",
        key_prefix=[PREFIX],
        group_name="catalog",
        deps=[SYNC_KEY, site_key],
        kinds={"openmetadata"},
        tags={"mcx": ""},
        description="The MCX vocabulary OpenMetadata cannot derive: the Commodities Ontology "
                    "glossary, Tier tags, glossary terms on columns, the Evidence dashboards and "
                    "Dagster pipelines as catalogue entities, and page ← model lineage "
                    "(catalog/mcx_ontology.py). Create-or-update, so reruns converge.",
    )
    def mcx_catalog(context: AssetExecutionContext) -> MaterializeResult:
        if not os.environ.get(TOKEN_ENV):
            raise RuntimeError(f"{TOKEN_ENV} is not set in the Dagster process — the catalogue "
                               "cannot be written. Export the ingestion-bot token before "
                               "`dagster dev` (docs/mcx.md, OpenMetadata).")
        onto = _load_ontology_module()
        counts = onto.apply(onto.build_payload())
        for kind, n in counts.items():
            context.log.info(f"openmetadata {kind}: {n}")
        return MaterializeResult(metadata={k: int(v) for k, v in counts.items()})

    return mcx_catalog


def catalog_request(run, instance, env=None):
    """What the catalogue sensor does after `run` succeeded: a RunRequest for
    the catalogue job, or a SkipReason saying why not."""
    from dagster import DagsterRunStatus, RunRequest, RunsFilter, SkipReason

    env = os.environ if env is None else env
    if not env.get(TOKEN_ENV):
        return SkipReason(f"{TOKEN_ENV} not set — catalogue publishing is off for this process")
    waiting = instance.get_runs(filters=RunsFilter(
        job_name=CATALOG_JOB,
        statuses=[DagsterRunStatus.QUEUED, DagsterRunStatus.NOT_STARTED, DagsterRunStatus.STARTING]))
    if waiting:
        return SkipReason(f"catalogue run {waiting[0].run_id[:8]} has not started yet; it will "
                          "publish this run's state too")
    return RunRequest(run_key=f"after-{run.run_id}",
                      tags={"mcx/after_run": run.run_id, "mcx/after_job": run.job_name,
                            **({"mcx/commodity": run.tags["mcx/commodity"]}
                               if "mcx/commodity" in run.tags else {})})


def _catalog_sensor(watched: list, catalog_job):
    """After any MCX job succeeds, publish the catalogue — as its own run, so a
    catalogue that is down or unauthorised never fails a day's market data.

    Runs that finish together coalesce: while a catalogue run is still waiting
    to start, a later success adds nothing, because that run will read the
    newer state anyway. Skipped, with the reason shown in the UI, when the
    process has no catalogue credential."""
    from dagster import DagsterRunStatus, run_status_sensor

    @run_status_sensor(
        name="mcx_catalog_after_run",
        run_status=DagsterRunStatus.SUCCESS,
        monitored_jobs=watched,
        request_job=catalog_job,
        default_status=DefaultSensorStatus.RUNNING,
        description="Publish MCX metadata to OpenMetadata after any MCX job succeeds.",
    )
    def mcx_catalog_after_run(context):
        return catalog_request(context.dagster_run, context.instance)

    return mcx_catalog_after_run


STAGGER_MINUTES = 3


def staggered(cron: str, slot: int) -> str:
    """`cron` moved `slot × STAGGER_MINUTES` later. Every commodity job writes the
    same DuckDB file and queues on its writer pool; starting them minutes apart
    keeps that queue short instead of sixteen runs arriving in the same second.
    A cron whose minute and hour are not plain numbers is left as written."""
    minute, hour, *rest = cron.split()
    if not (minute.isdigit() and hour.isdigit()):
        return cron
    total = int(hour) * 60 + int(minute) + slot * STAGGER_MINUTES
    return " ".join([str(total % 60), str((total // 60) % 24), *rest])


def _commodity_jobs(settings: dict[str, dict[str, str]], pipeline):
    """One job per commodity: its dlt load, then everything downstream of the
    MCX tables — the dbt models and their tests, then the Evidence build — so a
    commodity's job graph *is* the dlt → dbt → Evidence pipeline."""
    jobs, schedules = [], []
    for slot, (commodity, s) in enumerate(settings.items()):
        job = define_asset_job(
            name=f"mcx_{commodity}_ingest",
            selection=AssetSelection.assets(commodity_key(commodity)) | pipeline,
            tags={"mcx/commodity": commodity},
            description=f"MCX {commodity}: dlt load through its own pipeline (resumes from the "
                        "last committed batch), then dbt build of the MCX models and tests, "
                        "then the Evidence site. Other commodities are unaffected.",
        )
        jobs.append(job)
        schedules.append(ScheduleDefinition(
            name=f"mcx_{commodity}_daily",
            job=job,
            cron_schedule=staggered(s["cron"], slot),
            execution_timezone="Asia/Kolkata",
            default_status=(DefaultScheduleStatus.RUNNING if s["schedule"] == "running"
                            else DefaultScheduleStatus.STOPPED),
            tags={"mcx/commodity": commodity},
            description=f"Daily MCX {commodity} pipeline (dlt → dbt → Evidence). Toggle to "
                        "pause or resume it; others are unaffected.",
        ))
    return jobs, schedules


def mcx_definitions() -> Definitions:
    """Commodity assets, table specs, the semantic check, the audited site, the
    catalogue asset, jobs, schedules and the catalogue sensor. Merged over the
    factory's output in definitions.py; defines no resource, executor or pool."""
    wh = Warehouse.for_project(PROJECT_DIR, GROUP, PROJECT)
    settings = job_settings()
    commodities = list(settings)
    loaders = [_commodity_asset(wh, c) for c in commodities]
    semantic = _semantic_layer_asset(wh, commodities)
    site = _report_site_asset(wh, semantic.key)
    catalog = _catalog_asset(site.key)
    # Everything downstream of the MCX tables except the catalogue, which talks
    # to a server and has its own job, run by the sensor after this one: a
    # catalogue that is down must not fail a day's market data.
    pipeline = ((AssetSelection.assets(*INGEST_KEYS).downstream()
                 - AssetSelection.assets(SYNC_KEY, CATALOG_KEY))
                | AssetSelection.assets(AssetKey([PREFIX, "mcx_products"]))
                | AssetSelection.assets(semantic.key, site.key))
    jobs, schedules = _commodity_jobs(settings, pipeline)
    transform_job = define_asset_job(
        name=TRANSFORM_JOB,
        selection=pipeline,
        description="Rebuild only: dbt build of every MCX model and its tests, the semantic "
                    "check, then the Evidence site, without loading anything. For a model or "
                    "page change.",
    )
    # Sixteen commodity jobs rebuild the site sixteen times (the Evidence build
    # is minutes; the loads are seconds when current). The bulk job loads every
    # commodity — each through its own pipeline, one at a time on the writer
    # pool — then runs the downstream pass once. The per-commodity jobs stay the
    # way to rerun one commodity.
    all_job = define_asset_job(
        name=ALL_JOB,
        selection=AssetSelection.assets(*[commodity_key(c) for c in commodities]) | pipeline,
        tags={"mcx/scope": "all"},
        description="Every MCX commodity's dlt load, then one dbt build, semantic check, "
                    "Evidence build (audited) and Wren check. For a backfill or a missed "
                    "morning; a single commodity is its own mcx_<commodity>_ingest.",
    )
    catalog_job = define_asset_job(
        name=CATALOG_JOB,
        selection=AssetSelection.assets(SYNC_KEY, CATALOG_KEY),
        description="Refresh graph and MDL, publish tables, vocabulary and metrics "
                    "(catalog_sync), then the MCX glossary, tiers and lineage (mcx_catalog). "
                    "Launched by mcx_catalog_after_run after any MCX job succeeds.",
    )
    return Definitions(
        assets=[*loaders, _landed_tables_asset(wh, commodities), semantic, site, catalog],
        jobs=[*jobs, transform_job, all_job, catalog_job],
        schedules=schedules,
        sensors=[_catalog_sensor([*jobs, transform_job, all_job], catalog_job)],
    )
