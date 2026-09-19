"""Load this project end to end: dlt → DuckDB → annotations → dbt → manifests.

`pf seed commodity commodity-india` runs this. It is deliberately a plain script
so it works without a Dagster daemon. It needs network access: every price is
live from Yahoo Finance and gold-api.com.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_DIR / "src"))

from pf import obs  # noqa: E402
from pf.ontology.annotate import load_annotations  # noqa: E402
from pf.runtime.dbt_runtime import dbt, deps, parse  # noqa: E402
from pf.runtime.dlt_runtime import export_project_annotations, monitors_for, run_source  # noqa: E402
from pf.runtime.warehouse import Warehouse  # noqa: E402

GROUP = "commodity"
PROJECT = "commodity-india"


def main() -> int:
    wh = Warehouse.for_project(PROJECT_DIR, GROUP, PROJECT)
    from commodity_india.sources import gold_api, reference, yahoo_finance

    for name, source in (("reference", reference.reference_source()),
                         ("yahoo_finance", yahoo_finance.yahoo_finance_source()),
                         ("gold_api", gold_api.gold_api_source())):
        t0 = time.time()
        info = run_source(wh, source, source_name=name, dataset=name)
        obs.record_pipeline_run(group=GROUP, project=PROJECT, kind="dlt", name=name,
                                status="ok", duration_ms=int((time.time() - t0) * 1000),
                                message=f"loads={len(info['load_ids'])}")
        print(f"  dlt → {wh.path.name} dataset={name}")

    ann_path = export_project_annotations(PROJECT_DIR)
    anns = load_annotations(ann_path)
    print(f"  annotations → {ann_path.name} ({len(anns)} resources)")

    _run_monitors(wh, anns)

    deps(PROJECT_DIR, duckdb_path=wh.path)

    t0 = time.time()
    proc = dbt(PROJECT_DIR, "build", duckdb_path=wh.path)
    status = "ok" if proc.returncode == 0 else "error"
    obs.record_pipeline_run(group=GROUP, project=PROJECT, kind="dbt", name="build",
                            status=status, duration_ms=int((time.time() - t0) * 1000),
                            message=proc.stdout[-500:])
    print(f"  dbt build → {status}")
    if proc.returncode != 0:
        print(proc.stdout[-3000:])
        return proc.returncode

    parse(PROJECT_DIR, duckdb_path=wh.path)
    print("  dbt parse → manifest.json + semantic_manifest.json")
    return 0


def _run_monitors(wh: Warehouse, anns) -> None:
    """Execute the ontology-derived monitors and record their results."""
    monitors = monitors_for(anns)
    schema_of = {a.resource: a.source for a in anns}
    with wh.connect(read_only=True) as con:
        for m in monitors:
            table = f'{schema_of[m["resource"]]}.{m["resource"]}'
            try:
                if m["kind"] == "row_count_band":
                    n = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                    obs.record_monitor(group=GROUP, project=PROJECT, resource=m["resource"],
                                       column_name=m["column"], monitor=m["kind"],
                                       status="ok" if n > 0 else "critical",
                                       observed=n, expected=n, message=f"{n} rows")
                elif m["kind"] == "freshness":
                    row = con.execute(f'SELECT max({m["column"]}) FROM {table}').fetchone()[0]
                    obs.record_monitor(group=GROUP, project=PROJECT, resource=m["resource"],
                                       column_name=m["column"], monitor=m["kind"],
                                       status="ok", message=f"max={row}")
                elif m["kind"] == "category_drift":
                    cats = con.execute(
                        f'SELECT count(DISTINCT {m["column"]}) FROM {table}').fetchone()[0]
                    obs.record_monitor(group=GROUP, project=PROJECT, resource=m["resource"],
                                       column_name=m["column"], monitor=m["kind"],
                                       status="ok", observed=cats, expected=cats,
                                       message=f"{cats} distinct values")
            except Exception as exc:  # a monitor must never fail the load
                obs.record_monitor(group=GROUP, project=PROJECT, resource=m["resource"],
                                   column_name=m["column"], monitor=m["kind"],
                                   status="warn", message=str(exc)[:200])
    print(f"  monitors → {len(monitors)} generated from ontology roles")


if __name__ == "__main__":
    raise SystemExit(main())
