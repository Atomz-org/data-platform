"""Dagster entry point. The platform factory assembles everything —
never scaffold a raw Definitions object here.

`project_dir` is derived from __file__ so the definitions load identically from
`dagster dev`, a code location, or an ad-hoc python -c. Never rely on cwd.
"""

from pathlib import Path

from pf.runtime.dagster_runtime import build_definitions

PROJECT_DIR = Path(__file__).resolve().parents[2]

defs = build_definitions(
    group="globex",
    project="globex-eu",
    project_dir=PROJECT_DIR,
)
