"""Dagster entry point. The platform factory assembles everything —
never scaffold a raw Definitions object here.

`project_dir` is derived from __file__ so the definitions load identically from
`dagster dev`, a code location, or an ad-hoc python -c. Never rely on cwd.

Two departures from the ten-line default, both for MCX (`defs/mcx.py`):

* `source_modules` is explicit, leaving out `sources.mcx`. Auto-discovered, its
  resources would become one all-commodity ingest asset; MCX runs one job per
  commodity instead, over the same asset keys.
* The MCX jobs, schedules and sensor are merged over the factory's output. They
  add assets, jobs, schedules and a sensor only — no resource, executor or pool
  — so nothing the factory owns is shadowed. (The factory does not collect
  `defs/` itself yet; `Definitions.merge` is how a project adds to it.)
"""

from pathlib import Path

from dagster import Definitions
from pf.runtime.dagster_runtime import build_definitions

from commodity_india.defs.mcx import mcx_definitions

PROJECT_DIR = Path(__file__).resolve().parents[2]

defs = Definitions.merge(
    build_definitions(
        group="commodity",
        project="commodity-india",
        project_dir=PROJECT_DIR,
        source_modules=["commodity_india.sources.gold_api",
                        "commodity_india.sources.yahoo_finance"],
    ),
    mcx_definitions(),
)
