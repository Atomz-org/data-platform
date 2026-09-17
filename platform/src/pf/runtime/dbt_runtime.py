"""dbt Core wiring. The platform owns profiles, selectors and CLI invocation so
projects only own models.
"""

from __future__ import annotations

import json
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


#: dbt project keys whose files dbt writes back out under `target/`. Each file's
#: path relative to the project is joined onto target/ verbatim, so an entry that
#: climbs out of the project (`../../shared/seeds`) puts compiled SQL and seed
#: copies *beside* the project — generated files no ignore rule covers.
#: `macro-paths` and `docs-paths` are only read, and may point anywhere.
WRITTEN_PATH_KEYS = ("model-paths", "seed-paths", "test-paths", "snapshot-paths",
                     "analysis-paths", "asset-paths")


def escaping_paths(project_dir: str | Path) -> list[tuple[str, str]]:
    """(key, path) for every written-to dbt path that resolves outside the project.

    To share seeds across projects, install the directory holding them as a
    local package instead: a package's files compile under target/<package>/.
    `pf bootstrap` does that for a group's `shared/transform/seeds`.
    """
    import yaml

    transform = Path(project_dir) / "transform"
    spec = transform / "dbt_project.yml"
    if not spec.exists():
        return []
    try:
        doc = yaml.safe_load(spec.read_text()) or {}
    except yaml.YAMLError:
        return []
    base = transform.resolve()
    out: list[tuple[str, str]] = []
    for key in WRITTEN_PATH_KEYS:
        for entry in doc.get(key) or []:
            resolved = (base / str(entry)).resolve()
            if resolved != base and base not in resolved.parents:
                out.append((key, str(entry)))
    return out


def validate_paths(project_dir: str | Path) -> list[Any]:
    """`escaping_paths` as conformance issues, for `pf check` and bootstrap."""
    from pf.ontology.validate import ValidationIssue

    return [ValidationIssue(
        "error", "dbt-path-escapes-project", f"dbt_project.yml {key}",
        f"'{entry}' is outside the project, so dbt writes its compiled files "
        f"outside target/. Share seeds as a local package instead — "
        f"`pf bootstrap` wires groups/<group>/shared/transform when it has seeds.")
        for key, entry in escaping_paths(project_dir)]


def declared_packages(project_dir: str | Path) -> int:
    """How many packages `packages.yml` / `dependencies.yml` declare."""
    import yaml

    transform = Path(project_dir) / "transform"
    total = 0
    for name in ("packages.yml", "dependencies.yml"):
        f = transform / name
        if not f.exists():
            continue
        try:
            total += len((yaml.safe_load(f.read_text()) or {}).get("packages") or [])
        except yaml.YAMLError:
            continue
    return total


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


def ensure_manifest(project_dir: str | Path,
                    duckdb_path: str | Path | None = None) -> bool:
    """Produce `target/manifest.json` if it is not already there.

    The manifest is where the models, their columns and their lineage come
    from. Everything that reads it treats it as optional and degrades when it is
    missing — which is right for a card and wrong for a gate, because a gate
    with no models in front of it reports "nothing downstream" and passes.

    Installs packages first: dbt refuses to parse at all when `packages.yml`
    names packages that `dbt_packages/` does not hold, which is the state of
    every fresh checkout — and of a checkout whose packages.yml gained a group
    package after its last parse, which is why the count is checked even when
    a manifest already exists.

    Returns whether a manifest exists afterwards. Never raises — a project with
    no dbt project underneath it is a legitimate caller, and the old degraded
    behaviour is the right answer there.
    """
    transform = Path(project_dir) / "transform"
    manifest_path = transform / "target" / "manifest.json"
    if not (transform / "dbt_project.yml").exists():
        return manifest_path.exists()

    # Counted, not merely checked for emptiness: a checkout that has dbt_utils
    # installed but not a newly declared local package fails to parse exactly as
    # a fresh one does.
    declared = declared_packages(project_dir)
    installed = transform / "dbt_packages"
    have = sum(1 for _ in installed.iterdir()) if installed.is_dir() else 0
    try:
        if declared > have:
            deps(project_dir, duckdb_path=duckdb_path)
            parse(project_dir, duckdb_path=duckdb_path)
        elif not manifest_path.exists():
            parse(project_dir, duckdb_path=duckdb_path)
    except FileNotFoundError:
        pass  # dbt is not installed — the caller degrades as it always did
    return manifest_path.exists()


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
