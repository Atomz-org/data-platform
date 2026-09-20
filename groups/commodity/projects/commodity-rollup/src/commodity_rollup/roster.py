"""Which sisters this roll-up reads, by market alias.

The alias is the sister's project name without the group prefix (`commodity-us`
→ `us`): the platform rebuilds `<group>-<alias>` from it to find her Dagster
code location, and it is the catalog name her warehouse is attached under. Paths
are relative to this project and resolved by whoever uses them.

One list, imported by `definitions.py`, `seed.py` and the `sisters` source, so
adding a market to the roll-up is one line here and one row in the group's
`markets` seed.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[2]

SISTERS: dict[str, str] = {
    "india": "../commodity-india/data/commodity_india.duckdb",
    "us": "../commodity-us/data/commodity_us.duckdb",
}

#: The conformed marts every sister must present identically. The roll-up's
#: raw stage is the union of these; a sister whose columns differ is refused.
CONFORMED_TABLES: tuple[str, ...] = ("fct_landed_prices_daily",)


def sister_paths() -> dict[str, Path]:
    return {alias: (PROJECT_DIR / rel).resolve() for alias, rel in SISTERS.items()}
