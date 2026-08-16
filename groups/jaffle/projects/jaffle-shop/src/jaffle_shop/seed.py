"""Load this project end to end: seeds → DuckDB → dbt → manifests.

`pf seed jaffle jaffle-shop` runs this. It is deliberately a plain script so it
works without a Dagster daemon.

Unlike the acme projects there is no dlt source here: jaffle-shop's raw data is
58 CSVs under `transform/seeds/`, carried in the repo so the project builds
offline. They are gated behind dbt's `load_source_data` var — upstream
jaffle-shop's convention, kept so the models stay diffable against upstream —
so every dbt invocation below has to pass it or the seeds are disabled and
every staging model fails on a table that was never created.

Seeds are loaded in their own `dbt seed` before `dbt build`, and that ordering
is the point rather than an accident. The staging models read the seeded tables
as *sources*:

    select * from {{ source('ecom', 'raw_supplies') }}

dbt builds its DAG from `ref()` and `source()`, and a source is assumed to
pre-exist — so there is no edge from the seed that creates it. A single
`dbt build` on an empty warehouse runs the staging models concurrently with the
seeds they need, and 58 of them fail with `Catalog Error: Table with name
raw_supplies does not exist!` while the 1,539 models behind them skip. Running
it again passes, because by then the tables are there. Two invocations put the
edge back that the DAG cannot express.

`ref()`-ing the seeds instead would express it properly, but `ref()` to a
disabled node is a parse error, and the seeds are disabled by default — so that
fix and `load_source_data` cannot both exist.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_DIR / "src"))

from pf import obs                                             # noqa: E402
from pf.runtime.dbt_runtime import dbt, deps, parse             # noqa: E402
from pf.runtime.warehouse import Warehouse                     # noqa: E402

GROUP = "jaffle"
PROJECT = "jaffle-shop"

# Enables the seed directories in dbt_project.yml. Without it `dbt seed` loads
# nothing and reports success.
LOAD_SOURCE_DATA = ("--vars", "{load_source_data: true}")


def _run(wh: Warehouse, name: str, *args: str) -> int:
    t0 = time.time()
    proc = dbt(PROJECT_DIR, *args, *LOAD_SOURCE_DATA, duckdb_path=wh.path)
    status = "ok" if proc.returncode == 0 else "error"
    obs.record_pipeline_run(group=GROUP, project=PROJECT, kind="dbt", name=name,
                            status=status, duration_ms=int((time.time() - t0) * 1000),
                            message=(proc.stdout or proc.stderr)[-500:])
    print(f"  dbt {name} → {status}")
    if proc.returncode != 0:
        print((proc.stdout or proc.stderr)[-3000:])
    return proc.returncode


def main() -> int:
    wh = Warehouse.for_project(PROJECT_DIR, GROUP, PROJECT)
    wh.path.parent.mkdir(parents=True, exist_ok=True)

    deps(PROJECT_DIR, duckdb_path=wh.path)
    print("  dbt deps → packages installed")

    # First: the raw tables the staging models read as sources.
    if rc := _run(wh, "seed", "seed"):
        return rc
    # Then everything that reads them.
    if rc := _run(wh, "build", "build"):
        return rc

    parse(PROJECT_DIR, duckdb_path=wh.path)
    print("  dbt parse → manifest.json + semantic_manifest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
