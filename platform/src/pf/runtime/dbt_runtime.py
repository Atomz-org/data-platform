"""dbt Core wiring. The platform owns profiles, selectors and CLI invocation so
projects only own models.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

PROFILE_TEMPLATE = """\
{project}:
  target: "{{{{ env_var('DBT_TARGET', 'dev') }}}}"
  outputs:
    dev:
      type: duckdb
      path: "{{{{ env_var('PF_DUCKDB_PATH') }}}}"
      threads: 4
      extensions: [httpfs, json]
    ci:
      type: duckdb
      path: "{{{{ env_var('PF_DUCKDB_PATH') }}}}"
      threads: 8
    prod:
      type: duckdb
      path: "{{{{ env_var('PF_DUCKDB_PATH') }}}}"
      threads: 8
    # The comparison environment for a diff tool. Same database file, different
    # schema prefix, so `base_marts.fct_revenue` and `main_marts.fct_revenue`
    # both exist and can be queried against each other in one connection.
    #
    # This has to be a separate materialisation. Pointing a review tool at two
    # sets of dbt *artefacts* that resolve to the same relation makes every
    # value diff compare a table with itself and report clean — a false negative
    # on every change, which is worse than having no review at all.
    base:
      type: duckdb
      path: "{{{{ env_var('PF_DUCKDB_PATH') }}}}"
      schema: base
      threads: 4
      extensions: [httpfs, json]
"""


def write_profiles(project_dir: str | Path, project: str) -> Path:
    out = Path(project_dir) / "transform" / "profiles.yml"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(PROFILE_TEMPLATE.format(project=project.replace("-", "_")))
    return out


def dbt(project_dir: str | Path, *args: str, target: str = "dev",
        duckdb_path: str | Path | None = None, check: bool = False) -> subprocess.CompletedProcess:
    """Invoke dbt Core in a project's transform/ directory."""
    import os

    env = dict(os.environ)
    env["DBT_TARGET"] = target
    if duckdb_path:
        env["PF_DUCKDB_PATH"] = str(duckdb_path)
    transform = Path(project_dir) / "transform"
    return subprocess.run(
        ["dbt", *args, "--project-dir", str(transform), "--profiles-dir", str(transform)],
        env=env, capture_output=True, text=True, check=check,
    )


def deps(project_dir: str | Path, duckdb_path: str | Path | None = None) -> subprocess.CompletedProcess:
    """`dbt deps` — install packages.yml. Idempotent; safe to run every seed.

    Invalidates the partial-parse cache afterwards. Without this, macros from a
    newly installed package resolve as "'x' is undefined" until target/ is
    cleared by hand — dbt trusts the cached manifest over the new package.
    """
    proc = dbt(project_dir, "deps", duckdb_path=duckdb_path)
    # Drop the partial-parse cache: a newly installed package's macros otherwise
    # resolve as "'x' is undefined" until target/ is cleared by hand.
    (Path(project_dir) / "transform" / "target" / "partial_parse.msgpack").unlink(missing_ok=True)
    return proc


def parse(project_dir: str | Path, duckdb_path: str | Path | None = None) -> subprocess.CompletedProcess:
    """`dbt parse` — produces manifest.json, which the knowledge graph consumes."""
    return dbt(project_dir, "parse", duckdb_path=duckdb_path)


def manifest(project_dir: str | Path) -> dict[str, Any]:
    p = Path(project_dir) / "transform" / "target" / "manifest.json"
    return json.loads(p.read_text()) if p.exists() else {}


def run_results(project_dir: str | Path) -> dict[str, Any]:
    """run_results.json — the dbt Core replacement for the Cloud Jobs API.
    This is what the triage agent reads."""
    p = Path(project_dir) / "transform" / "target" / "run_results.json"
    return json.loads(p.read_text()) if p.exists() else {}


def failed_nodes(project_dir: str | Path) -> list[dict[str, Any]]:
    rr = run_results(project_dir)
    return [
        {
            "unique_id": r.get("unique_id"),
            "status": r.get("status"),
            "message": (r.get("message") or "")[:500],
            "execution_time": r.get("execution_time"),
        }
        for r in (rr.get("results") or [])
        if r.get("status") in ("error", "fail")
    ]


def modified_nodes(project_dir: str | Path, state_dir: str | Path,
                   duckdb_path: str | Path | None = None) -> list[str]:
    """`dbt ls -s state:modified+` — feeds impact analysis on a PR."""
    proc = dbt(project_dir, "ls", "--select", "state:modified+",
               "--state", str(state_dir), "--resource-type", "model",
               "--output", "name", duckdb_path=duckdb_path)
    if proc.returncode != 0:
        return []
    return [ln.strip() for ln in proc.stdout.splitlines() if ln.strip() and " " not in ln.strip()]


def mf_query(project_dir: str | Path, metrics: list[str], group_by: list[str],
             where: str = "", limit: int = 100) -> subprocess.CompletedProcess:
    """MetricFlow CLI — the dbt Core stand-in for the Cloud Semantic Layer API."""
    args = ["mf", "query", "--metrics", ",".join(metrics)]
    if group_by:
        args += ["--group-by", ",".join(group_by)]
    if where:
        args += ["--where", where]
    args += ["--limit", str(limit)]
    return subprocess.run(args, cwd=str(Path(project_dir) / "transform"),
                          capture_output=True, text=True)
