"""dbt Core wiring. The platform owns profiles, selectors and CLI invocation so
projects only own models.
"""

from __future__ import annotations

import json
import os
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
    out.write_text(PROFILE_TEMPLATE.format(project=project.replace("-", "_")), encoding="utf-8")
    return out


def dbt(project_dir: str | Path, *args: str, target: str = "dev",
        duckdb_path: str | Path | None = None, check: bool = False,
        hooks: bool = True) -> subprocess.CompletedProcess:
    """Invoke dbt Core in a project's transform/ directory.

    Every dbt invocation in this platform comes through here — `seed.py`,
    `pf seed`, `deps`, `parse` — which is what makes it the one place a
    before/after hook can be attached without each caller remembering to.

    The hooks fire only for `run` and `build`. `parse`, `deps`, `ls` and `debug`
    change nothing a per-project artefact would show, and firing on those would
    put three identical regenerations in front of every real one.

    `hooks=False` is for a caller that is *inside* a hook. Nothing does that
    today; it exists so that the first thing which does cannot recurse.

    dbt is a writer, so when the project's dev database is served by a quack
    server (`pf quack serve`), the invocation runs inside the write window —
    the server yields the file for the build and is back before this returns.
    A `prod` build touches a real warehouse, not the file, and skips the
    window; with no server running the window is a no-op.
    """
    import os

    from pf.runtime.quack import write_window

    env = dict(os.environ)
    env["DBT_TARGET"] = target
    if duckdb_path:
        env["PF_DUCKDB_PATH"] = str(duckdb_path)
    transform = Path(project_dir) / "transform"
    command = args[0] if args else ""

    if hooks:
        _run_hooks(project_dir, "before_dbt_run", command)
    # Hooks stay outside the window: they draw from the graph, not the served
    # database, and a slow hook must not hold the file away from the server.
    windowed = None if target == "prod" else env.get("PF_DUCKDB_PATH")
    with write_window(windowed):
        proc = subprocess.run(
            ["dbt", *args, "--project-dir", str(transform), "--profiles-dir", str(transform)],
            env=env, capture_output=True, text=True, check=check,
        )
    if hooks:
        _run_hooks(project_dir, "after_dbt_run", command)
    return proc


def _run_hooks(project_dir: str | Path, phase: str, command: str) -> None:
    """Per-project work bracketing a dbt run.

    Imported lazily and swallowed whole. A hook is a convenience — publishing a
    picture of the graph — and a broken one must never be able to fail a build
    that otherwise succeeded. The run is the thing that matters; the artefact is
    not, and the two must not share a fate.
    """
    try:
        from pf.atlas import run_phase

        run_phase(project_dir, phase, command)
    except Exception:  # noqa: BLE001 — see the docstring
        pass


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


def ensure_manifest(project_dir: str | Path, duckdb_path: str | Path | None = None) -> bool:
    """Produce `target/manifest.json` if it is missing or older than its inputs.

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
        elif manifest_is_stale(project_dir):
            parse(project_dir, duckdb_path=duckdb_path)
    except FileNotFoundError:
        pass  # dbt is not installed — the caller degrades as it always did
    return manifest_path.exists()


#: What dbt writes or installs under transform/, never what it reads.
_DBT_OUTPUTS = frozenset({"target", "dbt_packages", "logs"})
#: What dbt reads: models, sources, semantic models, exposures, macros, seeds.
_DBT_INPUTS = frozenset({".sql", ".yml", ".yaml", ".csv", ".py", ".md"})


def manifest_is_stale(project_dir: str | Path) -> bool:
    """Is `target/manifest.json` missing, or older than any file dbt parses?

    A manifest that merely exists was enough before, and it is how a laptop's
    graph came to lack every exposure a branch had added: the manifest was
    parsed before the exposures were written, `pf kg build` trusted it, and the
    graph committed from it was stale against the runner's, which has no
    manifest and parses fresh. Measured over the whole of transform/ rather
    than dbt_project.yml's path lists, so a project that adds a models path,
    a semantic layer or a seed directory is covered without naming it here.
    """
    transform = Path(project_dir) / "transform"
    manifest_path = transform / "target" / "manifest.json"
    if not manifest_path.exists():
        return True
    built = manifest_path.stat().st_mtime
    for here, dirs, files in os.walk(transform):
        # Pruned, not filtered: dbt_packages alone can hold thousands of files.
        # Hidden entries too: dbt keeps `.user.yml` beside profiles.yml, and a
        # file dbt writes on every run must not read as an edit.
        dirs[:] = [d for d in dirs if not d.startswith(".") and not (here == str(transform) and d in _DBT_OUTPUTS)]
        for name in files:
            if name.startswith(".") or Path(name).suffix not in _DBT_INPUTS:
                continue
            if (Path(here) / name).stat().st_mtime > built:
                return True
    return False


def manifest(project_dir: str | Path) -> dict[str, Any]:
    p = Path(project_dir) / "transform" / "target" / "manifest.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def run_results(project_dir: str | Path) -> dict[str, Any]:
    """run_results.json — the dbt Core replacement for the Cloud Jobs API.
    This is what the triage agent reads."""
    p = Path(project_dir) / "transform" / "target" / "run_results.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


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


def modified_nodes(project_dir: str | Path, state_dir: str | Path, duckdb_path: str | Path | None = None) -> list[str]:
    """`dbt ls -s state:modified+` — feeds impact analysis on a PR."""
    proc = dbt(
        project_dir,
        "ls",
        "--select",
        "state:modified+",
        "--state",
        str(state_dir),
        "--resource-type",
        "model",
        "--output",
        "name",
        duckdb_path=duckdb_path,
    )
    if proc.returncode != 0:
        return []
    return [ln.strip() for ln in proc.stdout.splitlines() if ln.strip() and " " not in ln.strip()]


def mf_env(project_dir: str | Path, target: str = "dev") -> dict[str, str]:
    """The environment MetricFlow needs: the same one `dbt()` builds.

    `mf` reads `profiles.yml`, and the profile resolves its DuckDB path from
    `PF_DUCKDB_PATH`. Running `mf` with the caller's environment left that
    unset, so every query — from `pf ask`, the MCP `query_metrics` tool and the
    onboarding metrics check — failed profile validation while `dbt build` in
    the same project succeeded. One function, used by every `mf` invocation.
    """
    import os

    project_dir = Path(project_dir).resolve()   # mf joins a relative dir onto cwd
    env = dict(os.environ)
    env.setdefault("DBT_TARGET", target)
    if not env.get("PF_DUCKDB_PATH"):
        module = project_dir.name.replace("-", "_")
        env["PF_DUCKDB_PATH"] = str((project_dir / "data" / f"{module}.duckdb").resolve())
    transform = project_dir / "transform"
    env.setdefault("DBT_PROFILES_DIR", str(transform))
    env.setdefault("DBT_PROJECT_DIR", str(transform))
    return env


def mf(project_dir: str | Path, *args: str, timeout: int = 300) -> subprocess.CompletedProcess:
    """Invoke the MetricFlow CLI in a project's transform/ with the right env.

    mf reads through dbt's adapter — a direct file open — so while a quack
    server owns the dev database, the file is borrowed for the query.
    """
    from pf.runtime.quack import write_window

    transform = Path(project_dir) / "transform"
    env = mf_env(project_dir)
    try:
        # utf-8 explicitly: mf prints ✔ and ✗, and on Windows the default codec
        # for a pipe is cp1252, which turns a successful query into a decode error.
        with write_window(env.get("PF_DUCKDB_PATH")):
            return subprocess.run(["mf", *args], cwd=str(transform), env=env,
                                  capture_output=True, text=True, encoding="utf-8",
                                  errors="replace", timeout=timeout)
    except FileNotFoundError:
        return subprocess.CompletedProcess(["mf", *args], 127, "",
                                           "mf not found — `uv sync` installs metricflow")
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(["mf", *args], 124, "",
                                           f"mf timed out after {timeout}s")


def mf_query(project_dir: str | Path, metrics: list[str], group_by: list[str],
             where: str = "", limit: int = 100) -> subprocess.CompletedProcess:
    """MetricFlow CLI — the dbt Core stand-in for the Cloud Semantic Layer API."""
    args = ["query", "--metrics", ",".join(metrics)]
    if group_by:
        args += ["--group-by", ",".join(group_by)]
    if where:
        args += ["--where", where]
    args += ["--limit", str(limit)]
    return mf(project_dir, *args)
