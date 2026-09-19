"""ADBC is how the platform talks to DuckDB: Arrow across every boundary.

Every pf-mediated connection — the warehouse factory's direct opens, the quack
read path's client — goes through Arrow Database Connectivity rather than the
duckdb Python DBAPI. Results move as Arrow record batches, which is the same
columnar shape DuckDB holds internally and the shape every consumer downstream
of pf (dataframes, BI, the MCP tools' serializers) wants anyway; rows exist
only at the last step, when a caller explicitly asks for them.

The driver is not an extra wheel: DuckDB's Python package compiles
``duckdb_adbc_init`` into its own extension module, so the ADBC driver manager
loads the exact library that is already installed. One engine, two doors, and
this module always takes the Arrow one.

What this module deliberately does not cover: the quack *server* process
(`pf.runtime.quack.serve_forever`) embeds duckdb directly — it calls
``quack_serve`` and holds the file, which is in-process embedding rather than
communication — and the tools that bring their own drivers (dbt-duckdb, dlt,
Evidence) speak to the same file through their own stacks inside the write
window.

`connect` returns a `Connection` whose ``execute`` chains like duckdb's
(``con.execute(sql).fetchall()``) so existing call sites read unchanged, while
``fetch_arrow`` / cursor ``fetch_arrow_table`` expose the batches directly.
"""

from __future__ import annotations

import glob
import sysconfig
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    import pyarrow as pa

_ENTRYPOINT = "duckdb_adbc_init"
_driver_cache: str | None = None


def driver_path() -> str:
    """The shared library exposing ``duckdb_adbc_init``.

    DuckDB's Python wheel ships it as the ``_duckdb`` extension module beside
    the ``duckdb`` package — located from the installed package, never from a
    hardcoded path, so a venv rebuild or version bump cannot silently point at
    a different engine than the rest of the platform uses.
    """
    global _driver_cache
    if _driver_cache is not None:
        return _driver_cache
    import duckdb

    site = Path(duckdb.__file__).resolve().parent.parent
    suffix = sysconfig.get_config_var("EXT_SUFFIX") or ".so"
    candidates = glob.glob(str(site / f"_duckdb*{suffix}")) or glob.glob(str(site / "_duckdb*.so"))
    if not candidates:
        raise RuntimeError(
            f"no _duckdb extension module under {site} — the installed duckdb "
            "wheel is expected to carry the ADBC entrypoint"
        )
    _driver_cache = candidates[0]
    return _driver_cache


class Connection:
    """The slice of duckdb's connection surface the platform uses, over ADBC.

    ``execute`` hands back the cursor, so ``con.execute(sql).fetchall()`` and
    ``.fetchone()`` chain exactly as they do on a duckdb connection — the
    difference is what crosses the boundary: Arrow batches, materialised to
    tuples only when a caller asks for rows.
    """

    def __init__(self, dbapi_con: Any):
        self._con = dbapi_con

    def execute(self, sql: str, parameters: Any | None = None):
        cur = self._con.cursor()
        if parameters is None:
            cur.execute(sql)
        else:
            cur.execute(sql, parameters)
        return cur

    def sql(self, sql: str):
        return self.execute(sql)

    def fetch_arrow(self, sql: str, parameters: Any | None = None) -> "pa.Table":
        """One statement, straight to an Arrow table."""
        return self.execute(sql, parameters).fetch_arrow_table()

    def close(self) -> None:
        self._con.close()

    def __getattr__(self, name: str):
        return getattr(self._con, name)


def connect(path: str | Path, read_only: bool = False) -> Connection:
    """An ADBC connection to a DuckDB database (or ``:memory:``).

    ``read_only`` maps to DuckDB's ``access_mode`` and is enforced by the
    engine — a CREATE on a read-only handle is refused, not ignored.
    Autocommit is on: the platform's writers are DDL-shaped and transactional
    batching belongs to the engines that need it (dbt), not this seam.
    """
    from adbc_driver_manager import dbapi

    db_kwargs: dict[str, str] = {"path": str(path)}
    if read_only:
        db_kwargs["access_mode"] = "read_only"
    return Connection(
        dbapi.connect(
            driver=driver_path(),
            entrypoint=_ENTRYPOINT,
            db_kwargs=db_kwargs,
            autocommit=True,
        )
    )
