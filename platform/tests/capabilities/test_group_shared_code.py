"""Group code is found by path; a roll-up refuses disagreeing sisters."""

import sys

import duckdb
import pytest
from pf.runtime.dagster_runtime import conformed_shapes
from pf.runtime.paths import extend_sys_path, import_paths


# ------------------------------------------------------------- import paths --
def _project(tmp_path, shared: bool):
    pdir = tmp_path / "groups" / "g" / "projects" / "g-us"
    (pdir / "src").mkdir(parents=True)
    if shared:
        (tmp_path / "groups" / "g" / "shared" / "python" / "src").mkdir(parents=True)
    return pdir


def test_a_group_without_shared_python_yields_only_the_project(tmp_path):
    pdir = _project(tmp_path, shared=False)
    assert import_paths(pdir) == [pdir.resolve() / "src"]


def test_the_group_shared_src_follows_the_project_src(tmp_path):
    pdir = _project(tmp_path, shared=True)
    assert import_paths(pdir) == [
        pdir.resolve() / "src",
        (tmp_path / "groups" / "g" / "shared" / "python" / "src").resolve(),
    ]


def test_extending_sys_path_is_idempotent_and_project_first(tmp_path, monkeypatch):
    pdir = _project(tmp_path, shared=True)
    monkeypatch.setattr(sys, "path", list(sys.path))
    added = extend_sys_path(pdir)
    assert [p.name for p in added] == ["src", "src"]
    assert sys.path[0] == str(pdir.resolve() / "src")
    assert sys.path[1].endswith("shared/python/src")
    assert extend_sys_path(pdir) == []


# ------------------------------------------------------ roll-up conformance --
def _sister(tmp_path, name, columns: dict[str, str]):
    path = tmp_path / f"{name}.duckdb"
    con = duckdb.connect(str(path))
    con.execute("CREATE SCHEMA main_marts")
    con.execute("CREATE TABLE main_marts.fct_landed_prices_daily ("
                + ", ".join(f"{c} {t}" for c, t in columns.items()) + ")")
    con.close()
    return path


def _attached(sisters):
    con = duckdb.connect()
    for alias, path in sisters.items():
        con.execute(f"ATTACH '{path}' AS {alias} (READ_ONLY)")
    return con


def test_identical_sisters_report_one_shape_per_table(tmp_path):
    cols = {"market_code": "varchar", "landed_price_local": "double"}
    sisters = {"india": _sister(tmp_path, "india", cols), "us": _sister(tmp_path, "us", cols)}
    shapes = conformed_shapes(_attached(sisters), sisters, ["fct_landed_prices_daily"])
    assert shapes == {"fct_landed_prices_daily": frozenset(cols)}


def test_a_sister_whose_columns_differ_is_refused_by_name(tmp_path):
    sisters = {
        "india": _sister(tmp_path, "india", {"market_code": "varchar", "landed_price_inr": "double"}),
        "us": _sister(tmp_path, "us", {"market_code": "varchar", "landed_price_local": "double"}),
    }
    with pytest.raises(ValueError, match="india: landed_price_inr; us: landed_price_local"):
        conformed_shapes(_attached(sisters), sisters, ["fct_landed_prices_daily"])


def test_a_sister_missing_the_table_is_refused(tmp_path):
    sisters = {"india": _sister(tmp_path, "india", {"market_code": "varchar"}),
               "us": _sister(tmp_path, "us", {"market_code": "varchar"})}
    with pytest.raises(ValueError, match=r"fct_revenue is missing in sister\(s\): india, us"):
        conformed_shapes(_attached(sisters), sisters, ["fct_revenue"])
