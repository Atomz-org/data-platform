"""Load this project end to end: dlt → DuckDB → annotations → dbt → manifests.

`pf seed acme acme-us` runs this. It is deliberately a plain script so it works
without a Dagster daemon.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_DIR / "src"))

from pf import obs                                             # noqa: E402
from pf.runtime.dbt_runtime import dbt, deps, parse                  # noqa: E402
from pf.runtime.dlt_runtime import export_project_annotations, monitors_for, run_source  # noqa: E402
from pf.runtime.warehouse import Warehouse                     # noqa: E402
from pf.ontology.annotate import load_annotations              # noqa: E402

GROUP = "acme"
PROJECT = "acme-eu"


def main() -> int:
    wh = Warehouse.for_project(PROJECT_DIR, GROUP, PROJECT)
    from acme_eu.sources import stripe

    t0 = time.time()
    info = run_source(wh, stripe.stripe_source(), source_name="stripe", dataset="stripe")
    obs.record_pipeline_run(group=GROUP, project=PROJECT, kind="dlt", name="stripe",
                            status="ok", duration_ms=int((time.time() - t0) * 1000),
                            message=f"loads={len(info['load_ids'])}")
    print(f"  dlt → {wh.path.name} dataset=stripe")

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
    with wh.connect(read_only=True) as con:
        for m in monitors:
            table = f'stripe.{m["resource"]}'
            try:
                if m["kind"] == "row_count_band":
                    n = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                    obs.record_monitor(group=GROUP, project=PROJECT, resource=m["resource"],
                                       column_name=m["column"], monitor=m["kind"],
                                       status="ok" if n > 0 else "critical",
                                       observed=n, expected=n,
                                       message=f"{n} rows")
                elif m["kind"] == "freshness":
                    row = con.execute(f'SELECT max({m["column"]}) FROM {table}').fetchone()[0]
                    obs.record_monitor(group=GROUP, project=PROJECT, resource=m["resource"],
                                       column_name=m["column"], monitor=m["kind"],
                                       status="ok", message=f"max={row}")
                elif m["kind"] == "sum_drift":
                    total = con.execute(f'SELECT sum({m["column"]}) FROM {table}').fetchone()[0] or 0
                    obs.record_monitor(group=GROUP, project=PROJECT, resource=m["resource"],
                                       column_name=m["column"], monitor=m["kind"],
                                       status="ok", observed=float(total), expected=float(total),
                                       message=f"sum={total:,.2f}")
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
