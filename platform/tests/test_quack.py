"""The quack dev server: state discipline, the write window, and the wire.

The integration tests spawn a real server process on a scratch database and
talk to it the way `Warehouse.connect` does — they are the proof that a served
project still reads, still builds, and hands the file back.
"""

from __future__ import annotations

import json
import os

import duckdb
import pytest
from pf.runtime import quack
from pf.runtime.warehouse import Warehouse


def test_derived_port_is_stable_and_in_range(tmp_path) -> None:
    db = tmp_path / "x.duckdb"
    port = quack.derived_port(db)
    assert port == quack.derived_port(db), "same path must derive the same port"
    assert quack.PORT_BASE <= port < quack.PORT_BASE + quack.PORT_SPAN


def test_stale_state_file_is_removed_not_believed(tmp_path) -> None:
    db = tmp_path / "x.duckdb"
    sp = quack.state_path(db)
    # A pid that is certainly gone: our own child would race, so use an absurd one.
    sp.write_text(json.dumps({"pid": 2**22 + 1, "port": 1, "token": "tttt", "database": str(db)}))
    assert quack.running_state(db) is None
    assert not sp.exists(), "a dead server's state file must be cleaned up"


def test_state_file_with_garbage_is_removed(tmp_path) -> None:
    db = tmp_path / "x.duckdb"
    quack.state_path(db).write_text("not json")
    assert quack.running_state(db) is None
    assert not quack.state_path(db).exists()


def test_write_window_without_server_is_a_noop(tmp_path) -> None:
    with quack.write_window(tmp_path / "x.duckdb"):
        pass
    with quack.write_window(None):
        pass


@pytest.fixture
def served(tmp_path):
    """A live quack server over a scratch database with one seeded table."""
    db = tmp_path / "data" / "srv.duckdb"
    db.parent.mkdir()
    con = duckdb.connect(str(db))
    con.execute("CREATE TABLE seeded AS SELECT 42 AS answer")
    con.close()
    state = quack.ensure(db)
    yield db, state
    quack.stop(db)


def test_serve_read_over_wire_and_write_window(served) -> None:
    db, state = served
    assert state.pid != os.getpid()
    assert quack.running_state(db) == state, "ensure() twice must find, not fork"
    assert quack.ensure(db) == state

    # Reads go over the wire exactly as Warehouse.connect does them.
    client = duckdb.connect()
    for stmt in state.attach_sql("served"):
        client.execute(stmt)
    client.execute("USE served")
    assert client.execute("SELECT answer FROM seeded").fetchone() == (42,)
    client.close()

    # Build schemas exist without any client having to create them.
    schemas = {
        s
        for (s,) in duckdb.connect()
        .execute("LOAD quack; CREATE SECRET (TYPE quack, TOKEN ?);", [state.token])
        .execute(f"ATTACH '{state.endpoint}' AS d")
        .execute("SELECT schema_name FROM duckdb_schemas() WHERE database_name='d'")
        .fetchall()
    }
    assert set(quack.DEFAULT_SCHEMAS) <= schemas

    # The write window yields a plain, writable file and re-serves afterwards.
    with quack.write_window(db):
        assert quack.running_state(db) is None
        writer = duckdb.connect(str(db))
        writer.execute("CREATE TABLE written_in_window AS SELECT 1 AS n")
        writer.close()
    after = quack.running_state(db)
    assert after is not None and after.pid != state.pid

    # And what was written in the window is visible over the new server.
    check = duckdb.connect()
    for stmt in after.attach_sql("d2"):
        check.execute(stmt)
    assert check.execute("SELECT n FROM d2.written_in_window").fetchone() == (1,)
    check.close()


def test_statement_gate_uses_the_real_parser() -> None:
    """Prefix matching is not a classifier — the parser is."""
    for ok in (
        "SELECT 1",
        "WITH x AS (SELECT 1) SELECT * FROM x",
        "DESCRIBE SELECT 1",
        "SHOW TABLES",
        "SUMMARIZE SELECT 1",
        "EXPLAIN SELECT 1",
        "PRAGMA database_list",
    ):
        quack.assert_read_only(ok)
    for bad in (
        "CREATE TABLE t(i INT)",
        "WITH x AS (SELECT 1 a) INSERT INTO t SELECT * FROM x",
        "DELETE FROM t",
        "CALL quack_stop('x')",
        "SET threads=1",
        "COPY t TO 'out.csv'",
        "SELECT 1; DROP TABLE t",
    ):
        with pytest.raises(PermissionError):
            quack.assert_read_only(bad)


def test_wire_is_read_only(served) -> None:
    """Two independent refusals: the client's parser and the engine itself."""
    db, state = served
    con = quack.read_connection(state)
    try:
        with pytest.raises(PermissionError, match="cannot cross the quack read path"):
            con.execute("CREATE TABLE smuggled AS SELECT 1")
        # Bypass the client gate entirely: raw passthrough with the real token.
        # The server holds the database read-only, so the engine refuses.
        quoted = "CREATE TABLE smuggled AS SELECT 1".replace("'", "''")
        with pytest.raises(Exception, match="read-only|Cannot execute"):
            con._con.execute(f"SELECT * FROM quack_query('{state.endpoint}', '{quoted}')").fetchall()
        assert con.execute("SELECT answer FROM seeded").fetchone() == (42,)
    finally:
        con.close()


def test_attach_sql_redacts_the_token(served) -> None:
    db, state = served
    shown = "\n".join(state.attach_sql("x"))
    redacted = "\n".join(state.attach_sql("x", redact=True))
    assert state.token in shown
    assert state.token not in redacted
    assert str(quack.state_path(db)) in redacted, "redaction must say where the token lives"


def test_custody_changes_are_recorded(tmp_path) -> None:
    """Serve, borrow and stop each land in the provenance ledger as full actions."""
    from pf.provenance import ledger

    root = tmp_path / "repo"
    (root / "platform").mkdir(parents=True)
    (root / "gate.yaml").write_text("version: 1\n")
    db = root / "groups" / "g" / "projects" / "p" / "data" / "p.duckdb"
    db.parent.mkdir(parents=True)

    quack.ensure(db)
    with quack.write_window(db):
        pass
    quack.stop(db)

    recorded = ledger.actions(root)
    summaries = [r["intent"].payload["summary"] for r in recorded.values() if "intent" in r]
    assert any("dev server up" in s for s in summaries)
    assert any("write window" in s for s in summaries)
    assert any("dev server stopped" in s for s in summaries)
    for stages in recorded.values():
        assert stages["intent"].tool == "pf.quack"
        assert stages["intent"].group == "g" and stages["intent"].project == "p"
        assert "execution" in stages, "every custody action must close with an execution record"


def test_warehouse_connect_routes_reads_over_quack(served, tmp_path) -> None:
    db, state = served
    wh = Warehouse(group="g", project="srv", path=db)
    with wh.connect(read_only=True) as con:
        assert isinstance(con, quack.ReadConnection), "read must go over the wire"
        assert con.quack_endpoint == state.endpoint
        assert con.execute("SELECT answer FROM seeded").fetchone() == (42,)
        # A schema-qualified base table is exactly what the ATTACH client
        # cannot fetch — the passthrough must resolve it server-side.
        assert con.execute("SELECT count(*) FROM main.seeded").fetchone() == (1,)
    # A writer through the same seam takes the window transparently.
    with wh.connect() as con:
        con.execute("CREATE TABLE via_connect AS SELECT 7 AS n")
    assert quack.running_state(db) is not None, "server must be back after a writer"
