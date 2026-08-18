"""Platform observability store — one DuckDB file at the repo root that records
everything you want to track: agent runs, token spend, monitor results, impact
reports and pipeline runs.

The UI reads this. The platform monitors itself with its own tooling.
"""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb

SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_runs (
    id TEXT PRIMARY KEY, ts TIMESTAMP, "group" TEXT, project TEXT,
    agent TEXT, model TEXT, effort TEXT, status TEXT,
    input_tokens BIGINT, output_tokens BIGINT,
    cache_read_tokens BIGINT, cache_write_tokens BIGINT,
    cost_usd DOUBLE, duration_ms BIGINT, summary TEXT, payload JSON
);
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id TEXT PRIMARY KEY, ts TIMESTAMP, "group" TEXT, project TEXT,
    kind TEXT, name TEXT, status TEXT, rows BIGINT,
    duration_ms BIGINT, message TEXT
);
CREATE TABLE IF NOT EXISTS monitor_results (
    id TEXT PRIMARY KEY, ts TIMESTAMP, "group" TEXT, project TEXT,
    resource TEXT, column_name TEXT, monitor TEXT, status TEXT,
    observed DOUBLE, expected DOUBLE, deviation_pct DOUBLE, message TEXT
);
CREATE TABLE IF NOT EXISTS impact_reports (
    id TEXT PRIMARY KEY, ts TIMESTAMP, "group" TEXT, project TEXT,
    root TEXT, severity TEXT, total INTEGER, report JSON
);
CREATE TABLE IF NOT EXISTS token_budgets (
    ts TIMESTAMP, "group" TEXT, project TEXT, artefact TEXT,
    tokens INTEGER, budget INTEGER, status TEXT
);
"""

# Pricing lives with the rest of each model's facts in `pf.agents.models`, so a
# new model is one edit rather than two that can drift apart.


def db_path(root: str | Path | None = None) -> Path:
    base = Path(root) if root else repo_root()
    return base / "data" / "_platform.duckdb"


def repo_root(start: str | Path | None = None) -> Path:
    p = Path(start or Path.cwd()).resolve()
    for candidate in [p, *p.parents]:
        if (candidate / "platform").is_dir() and (candidate / "groups").is_dir():
            return candidate
    return p


LOCK_RETRIES = 40
LOCK_BACKOFF_S = 0.15


@contextmanager
def connect(root: str | Path | None = None, read_only: bool = False) -> Iterator[duckdb.DuckDBPyConnection]:
    """Open the tracking DB, retrying while a sister project holds the writer lock.

    The platform's own metadata lives in DuckDB, so it inherits the same
    single-writer constraint the projects do. Sister pipelines run in parallel by
    design, so contention here is expected rather than exceptional.
    """
    path = db_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    if read_only and not path.exists():
        read_only = False

    con = None
    for attempt in range(LOCK_RETRIES):
        try:
            con = duckdb.connect(str(path), read_only=read_only)
            break
        except duckdb.IOException:
            if attempt == LOCK_RETRIES - 1:
                raise
            time.sleep(LOCK_BACKOFF_S)
    try:
        if not read_only:
            con.execute(SCHEMA)
        yield con
    finally:
        con.close()


def _now() -> datetime:
    return datetime.now(UTC)


def estimate_cost(model: str, input_tokens: int, output_tokens: int,
                  cache_read: int = 0, cache_write: int = 0,
                  ttl: str = "5m") -> float:
    """Cost of one call. Unknown models bill at Opus rates — over-reporting an
    unmapped model is the safe direction for a spend dashboard."""
    from pf.agents.models import UnknownModel, estimate_usd

    try:
        return estimate_usd(model, input_tokens, output_tokens, cache_read,
                            cache_write, ttl)
    except UnknownModel:
        return estimate_usd("claude-opus-5", input_tokens, output_tokens,
                            cache_read, cache_write, ttl)


def record_agent_run(*, group: str, project: str, agent: str, model: str,
                     effort: str = "medium", status: str = "ok",
                     input_tokens: int = 0, output_tokens: int = 0,
                     cache_read_tokens: int = 0, cache_write_tokens: int = 0,
                     duration_ms: int = 0, summary: str = "",
                     payload: dict[str, Any] | None = None,
                     root: str | Path | None = None) -> str:
    run_id = str(uuid.uuid4())
    cost = estimate_cost(model, input_tokens, output_tokens, cache_read_tokens, cache_write_tokens)
    with connect(root) as con:
        con.execute(
            "INSERT INTO agent_runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [run_id, _now(), group, project, agent, model, effort, status,
             input_tokens, output_tokens, cache_read_tokens, cache_write_tokens,
             cost, duration_ms, summary[:1000], json.dumps(payload or {})],
        )
    return run_id


def record_pipeline_run(*, group: str, project: str, kind: str, name: str,
                        status: str = "ok", rows: int = 0, duration_ms: int = 0,
                        message: str = "", root: str | Path | None = None) -> str:
    rid = str(uuid.uuid4())
    with connect(root) as con:
        con.execute("INSERT INTO pipeline_runs VALUES (?,?,?,?,?,?,?,?,?,?)",
                    [rid, _now(), group, project, kind, name, status, rows,
                     duration_ms, message[:1000]])
    return rid


def record_monitor(*, group: str, project: str, resource: str, column_name: str,
                   monitor: str, status: str, observed: float = 0.0,
                   expected: float = 0.0, deviation_pct: float = 0.0,
                   message: str = "", root: str | Path | None = None) -> str:
    rid = str(uuid.uuid4())
    with connect(root) as con:
        con.execute("INSERT INTO monitor_results VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    [rid, _now(), group, project, resource, column_name, monitor,
                     status, observed, expected, deviation_pct, message[:500]])
    return rid


def record_impact(*, group: str, project: str, root_node: str, severity: str,
                  total: int, report: dict[str, Any],
                  root: str | Path | None = None) -> str:
    rid = str(uuid.uuid4())
    with connect(root) as con:
        con.execute("INSERT INTO impact_reports VALUES (?,?,?,?,?,?,?,?)",
                    [rid, _now(), group, project, root_node, severity, total,
                     json.dumps(report)])
    return rid


def record_token_budget(*, group: str, project: str, artefact: str, tokens: int,
                        budget: int, root: str | Path | None = None) -> None:
    status = "ok" if tokens <= budget else "over"
    with connect(root) as con:
        con.execute("INSERT INTO token_budgets VALUES (?,?,?,?,?,?,?)",
                    [_now(), group, project, artefact, tokens, budget, status])


def query(sql: str, params: list | None = None, root: str | Path | None = None) -> list[dict]:
    """Read-only query against the tracking DB.

    Opened read_only so a dashboard refresh or a loop reading monitor results
    never takes the writer lock that recording pipeline runs needs.
    """
    with connect(root, read_only=True) as con:
        cur = con.execute(sql, params or [])
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row, strict=False)) for row in cur.fetchall()]
