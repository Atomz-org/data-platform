"""Every question through the semantic layer takes the same road, and the road
is recorded.

    [translate ─►] policy ─► plan ─► dry-run ─► execute ─► ledger

* **policy** — one statement, a `SELECT`, nothing that writes, attaches or
  configures. Checked with sqlglot, by statement type rather than by keyword,
  so a column called `load_date` is not a false alarm and a `COPY` hidden after
  a comment is not a false pass.
* **plan** — `wren dry-plan` against the LLM-facing manifest. A model or column
  that is not in that manifest does not plan; a column classified as personal
  data is not in it.
* **dry-run** — `EXPLAIN` of the planned SQL on the project's own warehouse,
  read-only. Wren's own `dry-run` cannot do this for DuckDB: its connector scans
  files and has no notion of the schemas a dbt build writes into (see
  `pf.tools.wren`). What it *would* prove — the physical tables exist and the
  query compiles — `EXPLAIN` proves the same way, without reading a row.
* **execute** — read-only, row-limited, through the same `Warehouse` every other
  part of the platform reads through. A query never travels through a second
  set of credentials.
* **translate** — a cube question (measures by dimensions, a time grain,
  filters) arrives as a structure, not SQL: `wren cube query --sql-only`
  turns it into one SELECT over the cube's base model, and that SELECT takes
  the rest of the road like any other. A structure that does not translate is
  refused and recorded here, keyed by the structure itself.
* **ledger** — every outcome, including the refused ones, appended to the
  group's `loop-ledger.json` as a `wren-query` run. That is the file the circuit
  breaker reads, and it is what makes the loop rule enforceable: a statement
  that has failed `MAX_ATTEMPTS` times is refused with "escalate" rather than
  tried a fourth time by an agent that forgot the first three.
"""

from __future__ import annotations

import hashlib
import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

LOOP = "wren-query"
DEFAULT_LIMIT = 200
MAX_LIMIT = 2000
#: The fallback when sqlglot cannot parse: a first word that is not a query, or
#: any word that changes state. Word-bounded, so `load_date` is a column.
FORBIDDEN = re.compile(
    r"\b(insert|update|delete|merge|drop|alter|create|attach|detach|copy|export|import|pragma|"
    r"install|load|call|set|reset|checkpoint|vacuum|truncate|grant|revoke|use|replace)\b", re.I)
COMMENT = re.compile(r"--[^\n]*|/\*.*?\*/", re.S)


@dataclass
class Outcome:
    ok: bool
    stage: str                 # translate | policy | plan | dry_run | execute | done
    sql: str
    planned_sql: str = ""
    columns: list[str] = field(default_factory=list)
    rows: list[dict[str, Any]] = field(default_factory=list)
    message: str = ""
    run_id: str = ""
    attempt: int = 1
    duration_ms: int = 0

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def sql_hash(sql: str) -> str:
    return hashlib.sha256(" ".join(sql.lower().split()).encode()).hexdigest()[:12]


# ----------------------------------------------------------------- policy --
def policy(sql: str) -> str | None:
    """Why this statement may not run, or None."""
    text = COMMENT.sub(" ", sql or "").strip().rstrip(";").strip()
    if not text:
        return "empty statement"
    if ";" in text:
        return "one statement per question"
    try:
        import sqlglot
        from sqlglot import exp

        parsed = sqlglot.parse(text, read="duckdb")
    except Exception:  # noqa: BLE001 — unparseable: judge the words instead
        head = text.split(None, 1)[0].lower()
        if head not in {"select", "with"}:
            return f"only a SELECT is planned; this starts with {head.upper()}"
        found = FORBIDDEN.search(text)
        return f"`{found.group(1).upper()}` changes state; only reads are planned" if found else None
    for node in parsed:
        if node is None:
            return "empty statement"
        if not isinstance(node, exp.Select | exp.Union | exp.Subquery):
            return f"only a SELECT is planned; this is {type(node).__name__.upper()}"
        for sub in node.walk():
            if isinstance(sub, exp.Command | exp.Create | exp.Drop | exp.Insert | exp.Update | exp.Delete
                          | exp.Merge | exp.Alter | exp.Set | exp.Pragma):
                return f"`{type(sub).__name__.upper()}` changes state; only reads are planned"
    return None


# ------------------------------------------------------------- warehouse --
def dry_run(warehouse: Path, planned_sql: str) -> str | None:
    """`EXPLAIN` on the project's warehouse, read-only. None when it compiles."""
    try:
        import duckdb

        con = duckdb.connect(str(warehouse), read_only=True)
        try:
            con.execute(f"EXPLAIN {planned_sql}")
        finally:
            con.close()
    except Exception as exc:  # noqa: BLE001 — the reason is the result
        return f"{type(exc).__name__}: {exc}"[:600]
    return None


def execute(warehouse: Path, planned_sql: str, limit: int) -> tuple[list[str], list[dict[str, Any]]]:
    import duckdb

    con = duckdb.connect(str(warehouse), read_only=True)
    try:
        rel = con.sql(planned_sql)
        columns = list(rel.columns)
        rows = [dict(zip(columns, r, strict=False)) for r in rel.fetchmany(limit)]
    finally:
        con.close()
    return columns, rows


# ----------------------------------------------------------------- ledger --
def attempts(root: Path, group: str, project: str, h: str) -> int:
    """How many times this exact statement has already failed here."""
    from pf.loops.runner import Ledger

    return sum(1 for e in Ledger(root, group).read()
               if e.get("loop") == LOOP and e.get("project") == project and e.get("outcome") != "ok"
               and str(e.get("message") or "").startswith(f"sha256:{h} "))


def record(root: Path, group: str, project: str, out: Outcome, started: datetime) -> str:
    from pf.loops.runner import Ledger, LoopRun

    h = sql_hash(out.sql)
    refused = out.stage in {"translate", "policy", "plan", "dry_run"}
    outcome = "ok" if out.ok else ("gate_blocked" if refused else "error")
    run = LoopRun(
        run_id=str(uuid.uuid4())[:8], loop=LOOP, group=group, project=project,
        started_at=started.isoformat(), outcome=outcome,
        findings=[] if out.ok else [f"{out.stage}: {out.message[:300]}"],
        tokens_used=0, duration_ms=out.duration_ms, attempt=out.attempt,
        message=f"sha256:{h} stage={out.stage} rows={len(out.rows)}",
    )
    Ledger(root, group).append(run)
    return run.run_id


# -------------------------------------------------------------------- ask --
def ask(project_dir: str | Path, group: str, project: str, sql: str,
        limit: int = DEFAULT_LIMIT, root: str | Path | None = None) -> Outcome:
    """One question, the whole road. Never raises: a refusal is an Outcome."""
    from pf import obs
    from pf.loops.runner import MAX_ATTEMPTS
    from pf.runtime.warehouse import Warehouse
    from pf.tools import wren as wt

    d = Path(project_dir)
    root_path = Path(root) if root else obs.repo_root(d)
    started = datetime.now(UTC)
    t0 = time.monotonic()
    limit = max(1, min(int(limit or DEFAULT_LIMIT), MAX_LIMIT))
    out = Outcome(ok=False, stage="policy", sql=sql, attempt=attempts(root_path, group, project, sql_hash(sql)) + 1)

    def finish() -> Outcome:
        out.duration_ms = int((time.monotonic() - t0) * 1000)
        out.run_id = record(root_path, group, project, out, started)
        return out

    if out.attempt > MAX_ATTEMPTS:
        out.message = (f"this statement has failed {MAX_ATTEMPTS} times here — escalate with the recorded "
                       "reasons rather than trying it again")
        return finish()
    reason = policy(sql)
    if reason:
        out.message = reason
        return finish()
    out.stage = "plan"
    planned = wt.plan(d, sql)
    if not planned.get("ok"):
        out.message = str(planned.get("message") or planned.get("reason") or "plan failed")
        return finish()
    out.planned_sql = str(planned.get("sql") or "")
    out.stage = "dry_run"
    wh = Warehouse.for_project(d, group, project)
    if not Path(wh.path).is_file():
        out.message = f"no warehouse at {wh.path} — run `pf seed {group} {project}`"
        return finish()
    err = dry_run(Path(wh.path), out.planned_sql)
    if err:
        out.message = err
        return finish()
    out.stage = "execute"
    try:
        out.columns, out.rows = execute(Path(wh.path), out.planned_sql, limit)
    except Exception as exc:  # noqa: BLE001 — a failed query is a result, not a crash
        out.message = f"{type(exc).__name__}: {exc}"[:600]
        return finish()
    out.ok, out.stage = True, "done"
    return finish()


def cube_spec(cube: str, measures: list[str], dimensions: list[str], time_dimension: str,
              filters: list[str]) -> str:
    """A cube question as one stable line: what the ledger keys a failed
    translation by, so the fourth identical attempt is refused like SQL's."""
    return (f"cube {cube} measures={','.join(measures)} dimensions={','.join(dimensions)} "
            f"time={time_dimension} filters={';'.join(sorted(filters))}")


def ask_cube(project_dir: str | Path, group: str, project: str, cube: str, measures: list[str],
             dimensions: list[str], time_dimension: str = "", filters: list[str] | None = None,
             limit: int = DEFAULT_LIMIT, root: str | Path | None = None) -> Outcome:
    """A cube question, the whole road: translate, then `ask`. Never raises."""
    from pf import obs
    from pf.loops.runner import MAX_ATTEMPTS
    from pf.tools import wren as wt

    d = Path(project_dir)
    root_path = Path(root) if root else obs.repo_root(d)
    limit = max(1, min(int(limit or DEFAULT_LIMIT), MAX_LIMIT))
    spec = cube_spec(cube, measures, dimensions, time_dimension, filters or [])
    translated = wt.translate_cube(d, cube, measures, dimensions, time_dimension, filters or [], limit)
    if translated.get("ok"):
        return ask(d, group, project, str(translated["sql"]), limit=limit, root=root_path)
    started = datetime.now(UTC)
    out = Outcome(ok=False, stage="translate", sql=spec,
                  attempt=attempts(root_path, group, project, sql_hash(spec)) + 1)
    out.message = (f"this cube question has failed {MAX_ATTEMPTS} times here — escalate with the recorded reasons"
                   if out.attempt > MAX_ATTEMPTS else str(translated.get("message") or "did not translate"))
    out.run_id = record(root_path, group, project, out, started)
    return out
