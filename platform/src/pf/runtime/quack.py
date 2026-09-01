"""The development database, served: a quack server per project.

Development still builds into one DuckDB file per project — that part of the
platform is untouched. What changes is who holds the file open. When a quack
server is up, the file belongs to the server process, every reader reaches the
database over ``quack:localhost:<port>`` (DuckDB's client-server protocol
extension, github.com/duckdb/duckdb-quack), and the two writers — dbt and dlt
— borrow the file back for exactly the duration of a build through
`write_window`. `Warehouse.connect` consults `running_state` and does the
right thing on both sides, so nothing above the runtime knows the difference.

## Why readers get the protocol and writers keep the file

The obvious design — dbt building over an ``ATTACH 'quack:...'`` — was tried
first and measured. The extension is experimental and its client-side surface
is partial: CREATE TABLE / CREATE VIEW into ``main`` work, INSERT and
transactions work, but schema DDL fails outright, view DDL outside ``main``
fails, DELETE is refused, and the local metadata views desync from the remote
catalog. ``quack_query()`` runs arbitrary SQL fully server-side and could in
principle carry a build, but routing dbt through it means rewriting every
materialisation. So the split follows DuckDB's own single-writer lock: one
writer on the file, any number of readers on the wire. Revisit when the
extension's ATTACH write surface grows up.

## The window is the coordination point, not a lock

`write_window` stops the server, yields the file, and restarts the server
afterwards — readers reconnect on their next query. That is acceptable in
development and wrong in production, which is one more reason production is a
real warehouse target (DuckLake — see `pf.runtime.targets`) and never a served
laptop file.

Everything here is keyed on the database *path*, not on group/project: the
state file sits beside the database it describes, which makes the association
impossible to lose and needs no registry.
"""

from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from zlib import crc32

#: Ports are derived, not configured: stable per database path, clashing only
#: as often as a 1000-slot hash table clashes. `serve` walks forward on a
#: genuinely busy port, and the state file records what was actually bound.
PORT_BASE = 46100
PORT_SPAN = 1000

#: Schemas the server pre-creates before listening. Schema DDL is exactly what
#: the quack client cannot send, so anything a client will write into has to
#: exist before the client shows up. dbt composes `<schema>_<layer>`; these are
#: the layers the scaffolder generates plus Elementary's audit schema. A build
#: that adds a new schema gets it on the next server start — `write_window`
#: restarts the server after every build, so "next start" is "immediately".
DEFAULT_SCHEMAS = (
    "main",
    "main_staging",
    "main_marts",
    "main_elementary",
    "base",
    "base_staging",
    "base_marts",
    "base_elementary",
)


@dataclass(frozen=True)
class QuackState:
    """What one running server wrote down about itself."""

    pid: int
    port: int
    token: str
    database: str

    @property
    def endpoint(self) -> str:
        return f"quack:localhost:{self.port}"

    def attach_sql(self, alias: str, redact: bool = False) -> tuple[str, ...]:
        """The statements a client runs to reach this server, in order.

        ``redact=True`` is for anything that prints: the token is replaced by
        a pointer to the state file it lives in, because a token echoed into a
        terminal outlives the server in scrollback, logs and transcripts. The
        redacted form is display text, not runnable SQL — that is the point.
        """
        token = f"<redacted — read it from {state_path(self.database)}>" if redact else self.token
        return (
            "INSTALL quack",
            "LOAD quack",
            f"CREATE SECRET IF NOT EXISTS (TYPE quack, TOKEN '{token}')",
            f"ATTACH '{self.endpoint}' AS {alias}",
        )


#: Statement types allowed to cross the read path. Everything else is refused
#: client-side before the network hop — and would be refused again by the
#: engine anyway, since the server holds the database read-only. EXPLAIN is
#: the only non-SELECT survivor; DESCRIBE, SHOW, SUMMARIZE and the read
#: pragmas all parse as SELECT.
READ_ONLY_STATEMENTS = frozenset({"SELECT", "EXPLAIN"})


def assert_read_only(sql: str) -> None:
    """Refuse anything that is not a read, using the real parser.

    A string prefix is not a classifier — ``WITH … INSERT INTO`` opens with
    the same characters as a query. ``duckdb.extract_statements`` runs
    DuckDB's own parser and names every statement in the string, and every one
    of them must be a read for the string to pass.
    """
    import duckdb

    for st in duckdb.extract_statements(str(sql)):
        name = st.type.name
        if name not in READ_ONLY_STATEMENTS:
            raise PermissionError(
                f"{name} cannot cross the quack read path — the dev server holds "
                "the database read-only. Writers borrow the file: use "
                "`Warehouse.connect()` without read_only, or `pf quack stop`."
            )


class ReadConnection:
    """Quacks like the slice of `DuckDBPyConnection` the read paths use,
    executing every statement server-side via ``quack_query``.

    Why not the obvious ``ATTACH 'quack:...'``: the experimental client
    resolves views and ``main``-schema tables over an attach, but drops the
    schema qualifier when fetching any other base table — ``main_marts.orders``
    errors as "Table with name orders does not exist". The ``quack_query``
    table function ships the statement whole into the server process, where
    every name resolves exactly as it would over a direct connection. Measured
    against a full jaffle-shop build: counts, joins, aggregates, DESCRIBE and
    catalog queries all correct via ``quack_query``; all broken via ATTACH.

    The local leg rides `pf.runtime.adbc`, so ``execute`` chains the way every
    pf connection does — ``con.execute(sql).fetchall()`` for rows,
    ``fetch_arrow`` for the batches themselves.
    """

    def __init__(self, con, state: QuackState):
        self._con = con
        self.quack_endpoint = state.endpoint

    def execute(self, sql: str, parameters: object | None = None):
        if parameters is not None:
            raise ValueError(
                "bind parameters cannot cross the quack read path — the statement is shipped as text; inline the values"
            )
        assert_read_only(sql)
        quoted = str(sql).replace("'", "''")
        return self._con.execute(f"SELECT * FROM quack_query('{self.quack_endpoint}', '{quoted}')")

    def sql(self, sql: str):
        return self.execute(sql)

    def fetch_arrow(self, sql: str):
        """One server-side statement, straight to an Arrow table."""
        return self.execute(sql).fetch_arrow_table()

    def close(self) -> None:
        self._con.close()

    def __getattr__(self, name: str):
        return getattr(self._con, name)


def read_connection(state: QuackState) -> ReadConnection:
    """A connection whose statements run inside the server owning the file.

    The local leg is ADBC (`pf.runtime.adbc`), so results come off the
    passthrough as Arrow batches like every other pf connection; the
    client-to-server leg is the quack extension's own protocol, which is the
    one part of the path this platform does not define."""
    from pf.runtime import adbc

    con = adbc.connect(":memory:")
    con.execute("INSTALL quack; LOAD quack;")
    con.execute(f"CREATE SECRET IF NOT EXISTS (TYPE quack, TOKEN '{state.token}')")
    return ReadConnection(con, state)


def state_path(db_path: str | Path) -> Path:
    return Path(db_path).with_suffix(".quack.json")


def derived_port(db_path: str | Path) -> int:
    return PORT_BASE + crc32(str(Path(db_path).resolve()).encode()) % PORT_SPAN


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    return True


def _listening(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def running_state(db_path: str | Path) -> QuackState | None:
    """The live server owning this database, or None.

    A state file whose process is gone is a leftover from a crash, not a
    server; it is removed on sight so a stale file can never wedge the write
    path.
    """
    sp = state_path(db_path)
    if not sp.exists():
        return None
    try:
        state = QuackState(**json.loads(sp.read_text()))
    except (json.JSONDecodeError, TypeError):
        sp.unlink(missing_ok=True)
        return None
    if not _alive(state.pid):
        sp.unlink(missing_ok=True)
        return None
    return state


# ---------------------------------------------------------------- custody --
def _repo_root(db_path: str | Path) -> Path | None:
    """The monorepo root above a warehouse file, or None outside one.

    Identified structurally — `platform/` and `groups/` beside a `gate.yaml` —
    never from cwd: custody records must land in the ledger of the repository
    the database belongs to, regardless of who asks from where.
    """
    for parent in Path(db_path).resolve().parents:
        if (parent / "platform").is_dir() and (parent / "groups").is_dir() and (parent / "gate.yaml").exists():
            return parent
    return None


def _group_project(db_path: str | Path) -> tuple[str, str]:
    parts = Path(db_path).resolve().parts
    if "groups" in parts:
        i = parts.index("groups")
        if len(parts) > i + 3 and parts[i + 2] == "projects":
            return parts[i + 1], parts[i + 3]
    return "", ""


@contextmanager
def _custody(db_path: str | Path, summary: str) -> Iterator[None]:
    """Record a change of warehouse custody in the provenance ledger.

    Serving, stopping and borrowing are the moments the development database
    changes hands, and each is an action like any other — intent, decision,
    execution, chained (`docs/GOVERNANCE.md`). The ledger's kill switch is
    honoured by construction: a revoked ledger refuses the custody record, and
    with it the custody change. Outside a platform checkout (unit tests on
    scratch paths) there is no ledger, and writing no record is the correct
    record.
    """
    root = _repo_root(db_path)
    if root is None:
        yield
        return
    from pf.provenance import action

    group, project = _group_project(db_path)
    with action(root, tool="pf.quack", target=str(db_path), summary=summary, group=group, project=project):
        yield


def _spawn(db_path: str | Path, timeout: float) -> QuackState:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(  # noqa: S603 — argv is built here, nothing user-shaped
        [sys.executable, "-m", "pf.runtime.quack", "serve", str(db_path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,  # survives the CLI that started it
    )
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = running_state(db_path)
        if state is not None and _listening(state.port):
            return state
        if proc.poll() is not None:
            raise RuntimeError(
                f"quack server for {db_path} exited with {proc.returncode} before "
                "listening — run `python -m pf.runtime.quack serve <db>` in the "
                "foreground to see why"
            )
        time.sleep(0.2)
    raise TimeoutError(f"quack server for {db_path} did not come up within {timeout}s")


def _terminate(db_path: str | Path, timeout: float) -> None:
    state = running_state(db_path)
    if state is None:
        return
    os.kill(state.pid, signal.SIGTERM)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _alive(state.pid):
            state_path(db_path).unlink(missing_ok=True)
            return
        time.sleep(0.1)
    os.kill(state.pid, signal.SIGKILL)
    state_path(db_path).unlink(missing_ok=True)


def ensure(db_path: str | Path, timeout: float = 15.0) -> QuackState:
    """A running server for this database — the one already up, or a new one.

    Starting a server is a custody change (the file stops being openable and
    starts being served) and is recorded in the provenance ledger.
    """
    state = running_state(db_path)
    if state is not None:
        return state
    with _custody(db_path, "dev server up — database now served read-only over quack"):
        return _spawn(db_path, timeout)


def stop(db_path: str | Path, timeout: float = 10.0) -> bool:
    """Stop the server owning this database. True if one was running. Recorded."""
    if running_state(db_path) is None:
        return False
    with _custody(db_path, "dev server stopped — database file released"):
        _terminate(db_path, timeout)
    return True


@contextmanager
def write_window(db_path: str | Path | None) -> Iterator[None]:
    """Yield the database file to a writer; restore the server afterwards.

    No server (or no path — a prod build has no file) means no-op, which is
    what lets dbt and dlt wrap every invocation unconditionally. A real window
    is one custody action in the ledger: the borrow is the intent, the body's
    outcome is the execution, and a body that raises is recorded as an error
    before the server comes back.
    """
    if db_path is None or running_state(db_path) is None:
        yield
        return
    with _custody(db_path, "write window — file borrowed from the dev server"):
        _terminate(db_path, timeout=10.0)
        try:
            yield
        finally:
            _spawn(db_path, timeout=15.0)


def serve_forever(db_path: str | Path, port: int | None = None) -> None:
    """Open the database, pre-create build schemas, listen until SIGTERM.

    Runs in its own process (`python -m pf.runtime.quack serve <db>`); `ensure`
    is how the rest of the platform starts it. The token is generated fresh per
    server and written to the state file (0600) beside the database — every
    client is local and reads it from there, and `pf quack status` prints it
    for anything that is not pf.
    """
    import secrets as pysecrets

    import duckdb

    db = Path(db_path)
    db.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db))
    con.execute("INSTALL quack; LOAD quack;")
    for schema in DEFAULT_SCHEMAS:
        con.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
    con.close()

    # The serving connection is read-only, so the wire cannot mutate the
    # database no matter what arrives on it — refused by the engine itself,
    # not by a parser or a callback that could be argued with. Writers never
    # meet this connection: they borrow the file through `write_window`.
    # The endpoint is localhost by construction — the host is not a
    # parameter, so a routable dev server cannot be configured into existence.
    con = duckdb.connect(str(db), read_only=True)
    con.execute("LOAD quack")

    port = derived_port(db) if port is None else port
    while _listening(port):  # hash clash or leftover listener — walk forward
        port += 1
    token = pysecrets.token_hex(16)
    con.execute(f"CALL quack_serve('quack:localhost:{port}', token='{token}')")

    sp = state_path(db)
    sp.write_text(
        json.dumps(
            asdict(
                QuackState(
                    pid=os.getpid(),
                    port=port,
                    token=token,
                    database=str(db),
                )
            )
        )
    )
    sp.chmod(0o600)

    stopping = False

    def _term(signum, frame):  # noqa: ARG001
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, _term)
    signal.signal(signal.SIGINT, _term)
    try:
        while not stopping:
            time.sleep(0.2)
    finally:
        sp.unlink(missing_ok=True)
        con.close()  # checkpoints; the file is clean for the next writer


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    if len(args) >= 2 and args[0] == "serve":
        port = int(args[2]) if len(args) > 2 else None
        serve_forever(args[1], port=port)
        return
    raise SystemExit("usage: python -m pf.runtime.quack serve <database> [port]")


if __name__ == "__main__":
    main()
