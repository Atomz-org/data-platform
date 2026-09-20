"""How a roll-up sees its sisters: their conformed marts, read-only, as Arrow.

A roll-up never imports a sister's code and never opens a sister's file for
writing. It attaches each sister's warehouse READ_ONLY to an in-memory DuckDB
and reads one mart at a time — the same `ATTACH ... (READ_ONLY)` the platform's
`Warehouse.attach_sisters` uses, but on a scratch connection so the read can be
consumed by a dlt extract while dlt itself holds the roll-up's own file for the
load. A served sister (`pf quack serve`) holds her file read-only too, so the
attach coexists with it.

Conformance is checked, not assumed: every sister must present the same column
set for a mart, or the union is refused with the differing columns named. Two
sisters that mean different things by `landed_price_local` cannot be summed,
and this is where that surfaces — loudly, rather than as a wrong number.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import duckdb

MARTS_SCHEMA = "main_marts"


def read_mart(sisters: dict[str, Path], table: str, schema: str = MARTS_SCHEMA,
              batch_rows: int = 50_000) -> Iterator[Any]:
    """Yield Arrow record batches of `schema.table` from every sister, in turn.

    Args:
        sisters: alias -> path of each sister's .duckdb file. A missing file is
            an error: a roll-up over a sister that has not been seeded would
            otherwise report her market as having no prices.
        table: the conformed mart, identical in shape in every sister.
    """
    missing = {a: p for a, p in sisters.items() if not Path(p).exists()}
    if missing:
        raise FileNotFoundError(
            "sister warehouse missing — seed it first: "
            + ", ".join(f"{a} ({p})" for a, p in missing.items()))
    con = duckdb.connect()
    try:
        for alias, path in sisters.items():
            con.execute(f"ATTACH '{path}' AS \"{alias}\" (READ_ONLY)")
        columns = {alias: _columns(con, alias, schema, table) for alias in sisters}
        _check_conformed(table, columns)
        for alias in sisters:
            reader = con.execute(f'SELECT * FROM "{alias}".{schema}.{table}').fetch_record_batch(batch_rows)
            yield from reader
    finally:
        con.close()


def _columns(con: duckdb.DuckDBPyConnection, alias: str, schema: str, table: str) -> list[str]:
    rows = con.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_catalog = ? AND table_schema = ? AND table_name = ? ORDER BY ordinal_position",
        [alias, schema, table]).fetchall()
    if not rows:
        raise LookupError(f"{alias} has no {schema}.{table}: not a conformed sister, or not built yet")
    return [r[0] for r in rows]


def _check_conformed(table: str, columns: dict[str, list[str]]) -> None:
    shapes = {alias: frozenset(cols) for alias, cols in columns.items()}
    if len(set(shapes.values())) <= 1:
        return
    common = frozenset.intersection(*shapes.values())
    diff = {alias: sorted(cols - common) for alias, cols in shapes.items() if cols - common}
    raise ValueError(
        f"{table} is not conformed across sisters — columns only some sisters have: "
        + "; ".join(f"{a}: {', '.join(c)}" for a, c in sorted(diff.items())))
