"""Dagster entry point. The platform factory assembles everything —
never scaffold a raw Definitions object here."""

from pf.runtime.dagster_runtime import build_definitions

defs = build_definitions(
    group="globex",
    project="globex-eu",
)
