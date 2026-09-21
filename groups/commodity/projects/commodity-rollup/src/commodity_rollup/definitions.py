"""Cross-entity roll-up. Attaches sister warehouses READ_ONLY.

The platform factory assembles everything — never scaffold a raw Definitions
object here. `project_dir` is derived from __file__ so the definitions load
identically from `dagster dev`, a code location, or an ad-hoc python -c.
"""

from pathlib import Path

from pf.runtime.dagster_runtime import build_definitions

from commodity_rollup.roster import CONFORMED_TABLES, SISTERS

PROJECT_DIR = Path(__file__).resolve().parents[2]

defs = build_definitions(
    group="commodity",
    project="commodity-rollup",
    project_dir=PROJECT_DIR,
    sisters=SISTERS,
    rollup_tables=CONFORMED_TABLES,
)
