"""ADBC is the platform's door into DuckDB — Arrow across the boundary."""

from __future__ import annotations

import pytest
from pf.runtime import adbc
from pf.runtime.warehouse import Warehouse


def test_driver_is_the_installed_duckdb_wheel() -> None:
    path = adbc.driver_path()
    assert "_duckdb" in path
    assert adbc.driver_path() is path, "second lookup must hit the cache"


def test_execute_chains_and_fetches_arrow(tmp_path) -> None:
    con = adbc.connect(tmp_path / "t.duckdb")
    try:
        con.execute("CREATE TABLE t AS SELECT 42 AS answer, 'arrow' AS proto")
        assert con.execute("SELECT answer FROM t").fetchone() == (42,)
        assert con.execute("SELECT * FROM t").fetchall() == [(42, "arrow")]
        tbl = con.fetch_arrow("SELECT * FROM t")
        assert tbl.schema.names == ["answer", "proto"]
        assert tbl.to_pylist() == [{"answer": 42, "proto": "arrow"}]
    finally:
        con.close()


def test_read_only_is_enforced_by_the_engine(tmp_path) -> None:
    rw = adbc.connect(tmp_path / "t.duckdb")
    rw.execute("CREATE TABLE t AS SELECT 1 a")
    rw.close()
    ro = adbc.connect(tmp_path / "t.duckdb", read_only=True)
    try:
        assert ro.execute("SELECT a FROM t").fetchone() == (1,)
        with pytest.raises(Exception, match="read-only|Cannot execute"):
            ro.execute("CREATE TABLE t2 AS SELECT 2 b")
    finally:
        ro.close()


def test_warehouse_hands_out_adbc_connections(tmp_path) -> None:
    wh = Warehouse(group="g", project="p", path=tmp_path / "data" / "p.duckdb")
    with wh.connect() as con:
        assert isinstance(con, adbc.Connection)
        con.execute("CREATE TABLE t AS SELECT 7 n")
    with wh.connect(read_only=True) as con:
        assert isinstance(con, adbc.Connection)
        assert con.fetch_arrow("SELECT n FROM t").to_pylist() == [{"n": 7}]
