"""A roll-up reads its sisters' conformed marts, and refuses ones that disagree."""

import duckdb
import pyarrow as pa
import pytest
from commodity_shared import sisters


def _sister(tmp_path, name, columns):
    path = tmp_path / f"{name}.duckdb"
    con = duckdb.connect(str(path))
    con.execute("CREATE SCHEMA main_marts")
    cols = ", ".join(f"{c} {t}" for c, t in columns.items())
    con.execute(f"CREATE TABLE main_marts.fct_landed_prices_daily ({cols})")
    con.execute(
        "INSERT INTO main_marts.fct_landed_prices_daily VALUES ("
        + ", ".join("?" for _ in columns) + ")",
        [name.upper(), "gold", 1.0][: len(columns)])
    con.close()
    return path


def test_reads_every_sister_in_turn(tmp_path):
    cols = {"market_code": "varchar", "commodity_id": "varchar", "landed_price_local": "double"}
    paths = {"in": _sister(tmp_path, "in", cols), "us": _sister(tmp_path, "us", cols)}
    table = pa.Table.from_batches(list(sisters.read_mart(paths, "fct_landed_prices_daily")))
    assert sorted(table.column("market_code").to_pylist()) == ["IN", "US"]


def test_a_sister_with_a_different_shape_is_refused_by_name(tmp_path):
    india = {"market_code": "varchar", "commodity_id": "varchar", "landed_price_inr": "double"}
    us = {"market_code": "varchar", "commodity_id": "varchar", "landed_price_local": "double"}
    paths = {"in": _sister(tmp_path, "in", india), "us": _sister(tmp_path, "us", us)}
    with pytest.raises(ValueError, match="in: landed_price_inr; us: landed_price_local"):
        list(sisters.read_mart(paths, "fct_landed_prices_daily"))


def test_a_missing_sister_is_an_error_not_an_empty_market(tmp_path):
    cols = {"market_code": "varchar", "commodity_id": "varchar", "landed_price_local": "double"}
    paths = {"in": _sister(tmp_path, "in", cols), "us": tmp_path / "never_seeded.duckdb"}
    with pytest.raises(FileNotFoundError, match="us"):
        list(sisters.read_mart(paths, "fct_landed_prices_daily"))


def test_a_sister_without_the_mart_is_named(tmp_path):
    cols = {"market_code": "varchar", "commodity_id": "varchar", "landed_price_local": "double"}
    paths = {"in": _sister(tmp_path, "in", cols)}
    with pytest.raises(LookupError, match=r"in has no main_marts\.fct_prices"):
        list(sisters.read_mart(paths, "fct_prices"))
