"""Recce — the empirical half of impact analysis.

`pf impact` reads the knowledge graph and reports what *could* break when a model
changes: which marts sit downstream, which metrics read them, which exposure the
CFO opens on Monday. It is a structural answer and it is available before
anything runs.

Recce answers the other half. It builds the changed project against a baseline
and reports what *did* change: rows that appeared, a schema that shifted, a
revenue total that moved four percent. Structural blast radius and empirical
diff are different questions, and a platform that gates merges on the first
without ever asking the second is trusting lineage to predict arithmetic.

This module is also the reference implementation of `pf.tools`. Everything the
platform needs from Recce is declared in `TOOL` below; nothing about Recce
appears in the scaffolder, the bootstrap list, the Dagster factory, the CLI or
the UI. If this module were deleted and its entry removed from
`registry.BUILTIN_MODULES`, the platform would lose the tool and nothing else.

## The baseline is the hard part

A diff needs two states. dbt gives us `target/` for the current build; the
comparison state has to come from somewhere, and every option is a trade:

  * **`target-base/` captured from a known-good build** — what we do. `pf tool
    recce baseline` copies the current artefacts aside after a green run, so the
    baseline is a state this machine actually produced.
  * Fetching it from an artefact registry — better, and now what we also do.
    `pf.artifacts` publishes the captured baseline to a bucket keyed by the ref
    it was built from, so a CI runner with code and no warehouse pulls the
    baseline main produced instead of failing to build one.

A baseline that was never captured is a *distinct state* from a project with no
manifest, which is why `DbtBinding.needs_baseline` exists rather than folding
both into "not ready". The first is one command away; the second means the
project has never been built.

## Where the artefacts live

Not in git. `recce_state.json` and `target-base/` were committed once, for a
good reason — a reviewer on another machine cannot reproduce a summary's numbers
without the baseline it was measured against — and the reason did not survive
contact with a project that has 996 marts and 30 MB of them, rewritten whole on
every run. They now go to the bucket `pf.artifacts` describes, under keys that
mirror this repository's own layout, and the commands below push and pull them
without the caller thinking about it. With no bucket configured, everything
here behaves exactly as it did when the files were local-only.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pf import artifacts
from pf.capabilities import Capability
from pf.tools.spec import (
    DbtBinding, Requirement, Surface, Tool, ToolContext, ToolContribution,
)

# Recce's own constants, mirrored here so a rename upstream shows up as a vendor
# drift finding against `recce/constants.py` rather than as a config file nobody
# reads. See the `recce` entry in platform/src/pf/vendor/registry.yaml.
CONFIG_FILE = "recce.yml"
STATE_FILE = "recce_state.json"
SUMMARY_FILE = "recce_summary.md"
BASELINE_DIR = "target-base"
DEFAULT_PORT = 8000

#: Key segment holding recorded reviews in the artefact bucket. It has no local
#: counterpart — on disk a review is two files sitting in `transform/`, because
#: a checkout only ever holds one. The bucket holds every branch's at once, so
#: it needs somewhere to put them.
REVIEWS_DIR = "reviews"

# Artefacts dbt writes that Recce compares. `catalog.json` only exists after
# `dbt docs generate`; the column-level checks need it, the structural ones do
# not, so a missing catalog degrades the diff rather than failing it.
BASELINE_ARTEFACTS = ("manifest.json", "catalog.json")


# ------------------------------------------------------------------ paths --
def dbt_dir(project_dir: Path) -> Path:
    return Path(project_dir) / "transform"


def config_file(project_dir: Path) -> Path:
    return dbt_dir(project_dir) / CONFIG_FILE


def state_file(project_dir: Path) -> Path:
    return dbt_dir(project_dir) / STATE_FILE


def summary_file(project_dir: Path) -> Path:
    return dbt_dir(project_dir) / SUMMARY_FILE


def baseline_dir(project_dir: Path) -> Path:
    return dbt_dir(project_dir) / BASELINE_DIR


def has_manifest(project_dir: Path) -> bool:
    return (dbt_dir(project_dir) / "target" / "manifest.json").exists()


def has_baseline(project_dir: Path) -> bool:
    return (baseline_dir(project_dir) / "manifest.json").exists()


def has_data(project_dir: Path) -> bool:
    """Is there a warehouse with anything in it?

    Every value-level check (row counts, value diffs, profiles) queries both
    sides. A checkout has code and no warehouse — the duckdb file is generated
    by `pf seed`, never committed — so on CI the answer is no, and the review
    that can still run is the structural one.
    """
    import duckdb

    p = Path(dbt_env(project_dir)["PF_DUCKDB_PATH"])
    if not p.exists():
        return False
    try:
        con = duckdb.connect(str(p), read_only=True)
    except duckdb.Error:
        return False  # a sister holds the write lock — assume it has data
    try:
        return bool(con.execute(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema NOT IN ('information_schema','pg_catalog') LIMIT 1"
        ).fetchone())
    except duckdb.Error:
        return False
    finally:
        con.close()


# ----------------------------------------------------------------- config --
# The only tool-specific mapping in this module: an ontology review *intent*
# becomes a recce check type. The intents themselves live in the ontology
# (`platform/src/pf/ontology/concepts.yaml`), so a role added there is reviewed
# here with no edit to this file — and a different review tool translates the
# same intents into its own vocabulary.
#
# `identity` is absent on purpose: it is not a check, it is the key a value diff
# aligns rows on.
INTENT_CHECKS: dict[str, str] = {
    "distribution": "profile_diff",
    "categories": "query_diff",
}


@dataclass(frozen=True)
class ReviewColumn:
    name: str
    role: str
    intent: str
    pii: bool


@dataclass(frozen=True)
class ReviewModel:
    """One model, described in the ontology's terms rather than the warehouse's."""

    name: str
    grain: str
    columns: tuple[ReviewColumn, ...]

    @property
    def key(self) -> str:
        """First identity column that is safe to key on, or empty."""
        return next((c.name for c in self.columns
                     if c.intent == "identity" and not c.pii), "")

    def comparable(self) -> list[str]:
        """Columns a value diff may materialise — everything except PII."""
        return [c.name for c in self.columns if not c.pii]

    def by_intent(self, intent: str) -> list[str]:
        return [c.name for c in self.columns if c.intent == intent and not c.pii]

    @property
    def redacted(self) -> list[str]:
        return [c.name for c in self.columns if c.pii]


def generate_config(project_dir: Path) -> dict[str, Any]:
    """Build recce.yml from what the ontology already says about this project.

    Upstream ships `recce init`, which is interactive and produces two generic
    checks. We can do better without asking anyone anything, because the meaning
    of every column is already declared. The chain is:

        annotations.yaml  column -> role
        concepts.yaml     role   -> review intent   (+ pii flag)
        INTENT_CHECKS     intent -> recce check type

    Nothing in this function names a role. Add `discount_pct: {datatype: decimal}`
    to the ontology and it is profiled on the next `pf bootstrap`; add
    `plan_tier: {datatype: string, review: categories}` and its category drift is
    watched. That is the whole point — one edit to the ontology updates cleaning,
    tests, monitors *and* review checks together.

    Falls back to the two structural checks when the graph is empty — a freshly
    scaffolded project has no models, and emitting checks against nothing would
    fail on first run.
    """
    checks: list[dict[str, Any]] = [
        {"name": "Row count diff",
         "description": "Row counts for every modified table model.",
         "type": "row_count_diff",
         "params": {"select": "state:modified,config.materialized:table"}},
        {"name": "Schema diff",
         "description": "Column additions, removals and type changes.",
         "type": "schema_diff"},
    ]

    for model in _reviewable_models(project_dir):
        # The grain, not a concept. A mart fans in from several annotated
        # resources — fct_payments joins Payment, Customer and Subscription — so
        # there is no single concept to name it with, and picking one would put a
        # wrong fact in a description a reviewer is meant to trust. The grain is
        # the ontology's statement of what one row means, and it is unambiguous.
        subject = model.grain or model.name

        # A value diff needs a key to align rows on. Aggregate marts often have
        # none — one row per day/segment/plan with no surrogate — and requiring
        # one would leave exactly those models, where a changed metric filter
        # hides, with no value-level coverage at all.
        if model.key:
            params: dict[str, Any] = {"model": model.name, "primary_key": model.key}
            redacted = model.redacted
            if redacted:
                # Explicit column list rather than "all columns". A value diff
                # writes the compared rows into recce_state.json, which is
                # durable and shared, so a PII column here would persist real
                # addresses into a review artefact.
                params["columns"] = model.comparable()
            checks.append({
                "name": f"Value diff — {model.name}",
                "description": (f"Row-level differences in {model.name} "
                                f"({subject}), keyed on {model.key}."
                                + (f" Excludes {len(redacted)} PII column(s)."
                                   if redacted else "")),
                "type": "value_diff",
                "params": params,
            })

        # Distribution checks take a column list, so one check per model covers
        # every magnitude it carries.
        distribution = model.by_intent("distribution")
        if distribution:
            checks.append({
                "name": f"Profile diff — {model.name}",
                "description": (f"Distribution of {', '.join(distribution)} "
                                f"({subject}). A shifted total is the failure "
                                f"lineage cannot predict."),
                "type": "profile_diff",
                "params": {"model": model.name, "columns": distribution},
            })

        # Category drift as a keyed group-by rather than recce's `top_k_diff`.
        #
        # top_k_diff is the obvious choice and it does not work for this. It
        # returns parallel arrays — `values: [growth, basic, ...]`,
        # `counts: [721, 0, ...]` — and recce compares results with
        # `DeepDiff(..., ignore_order=True)`. Renaming a category moves a count
        # between two slots, so both arrays stay equal *as multisets* and the
        # drift is invisible: verified against a real rename, where the check ran
        # green while `starter` had become `basic`.
        #
        # A `query_diff` keyed on the category returns one row per value, so the
        # same rename shows up as a row that exists on one side only. Same
        # question, a comparison that can actually answer it.
        for col in model.by_intent("categories"):
            checks.append({
                "name": f"Category drift — {model.name}.{col}",
                "description": (f"Values gained or lost in {col} ({subject}). "
                                f"A category that appears or disappears breaks an "
                                f"accepted_values test downstream without moving "
                                f"the row count."),
                "type": "query_diff",
                "params": {
                    "sql_template": (f"select {col} as category, count(*) as n "
                                     f"from {{{{ ref('{model.name}') }}}} "
                                     f"group by 1 order by 1"),
                    "primary_keys": ["category"],
                },
            })
    return {"checks": checks}


def _reviewable_models(project_dir: Path) -> list[ReviewModel]:
    """Every mart, described by ontology role and review intent.

    Reads the knowledge graph rather than the dbt manifest: the graph already
    carries the role and the resolved `pii` flag per column, which the manifest
    does not. A project whose graph is missing or empty yields nothing, and the
    caller degrades to the structural checks.

    Staging is excluded by contract — it is 1:1 with a raw table, so a value
    diff there restates what the row-count check already says at many times the
    cost, and staging is where the PII lives.
    """
    gp = Path(project_dir) / "kg" / "graph.duckdb"
    if not gp.exists():
        return []
    try:
        from pf.kg.store import open_graph
        from pf.ontology.model import load_ontology
    except Exception:  # noqa: BLE001 — graph tooling missing is not fatal here
        return []

    try:
        onto = load_ontology()
        out: list[ReviewModel] = []
        with open_graph(gp, read_only=True) as g:
            for m in g.nodes("Model"):
                if (m.layer or "") != "marts":
                    continue
                cols: list[ReviewColumn] = []
                for e in g.out_edges(m.id):
                    col = g.node(e.dst)
                    if col is None or col.kind != "Column":
                        continue
                    props = col.props or {}
                    role_name = props.get("role") or ""
                    role = onto.roles.get(role_name)
                    # The graph's `pii` flag is the ontology's verdict already
                    # materialised; trusting it means a group ontology that adds
                    # its own PII role is covered without touching this module.
                    pii = bool(props.get("pii")) or bool(role and role.pii)
                    intent = role.review_intent if role else "none"
                    cols.append(ReviewColumn(col.name, role_name,
                                             "none" if pii else intent, pii))
                if any(c.intent != "none" for c in cols):
                    out.append(ReviewModel(
                        name=m.name,
                        grain=(m.props or {}).get("grain", ""),
                        columns=tuple(cols),
                    ))
    except Exception:  # noqa: BLE001 — a half-built graph must not break bootstrap
        return []
    return sorted(out, key=lambda r: r.name)



def write_config(project_dir: Path) -> tuple[Path, bool]:
    """Write recce.yml if it would change. Returns (path, changed).

    Idempotent because `pf bootstrap` runs on every project on every upgrade,
    and a step that rewrites a file unconditionally turns `git status` into
    noise that people learn to ignore.
    """
    import yaml

    path = config_file(project_dir)
    body = ("# GENERATED by `pf bootstrap`. Do not edit.\n"
            "#\n"
            "# Every check below is derived, not written:\n"
            "#\n"
            "#   contracts/annotations.yaml   column -> ontology role\n"
            "#   ontology concepts.yaml       role   -> review intent, pii flag\n"
            "#   pf.tools.recce               intent -> check type\n"
            "#\n"
            "# So the way to change a check is to fix what the column *means*, not\n"
            "# to edit here: a wrong check is a wrong role. Columns whose role is\n"
            "# PII are excluded from every value-level check, because this file's\n"
            "# results land in recce_state.json, which is durable and shared.\n"
            "#\n"
            "# Regenerate with `pf tool recce config <group> <project>`.\n"
            + yaml.safe_dump(generate_config(project_dir), sort_keys=False))
    if path.exists() and path.read_text() == body:
        return path, False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    return path, True


def ensure_base_target(project_dir: Path, project: str = "") -> bool:
    """Make sure profiles.yml has the `base` output a diff needs. Returns True if
    it was added.

    Projects scaffolded before the `base` target existed would otherwise fail
    the baseline build with "target not found" — the same retrofit problem
    `pf bootstrap` exists to solve, so it is solved the same way. profiles.yml is
    generated by the platform, so rewriting it from the template is safe.
    """
    import yaml

    from pf.runtime.dbt_runtime import write_profiles

    path = dbt_dir(project_dir) / "profiles.yml"
    if path.exists():
        try:
            doc = yaml.safe_load(path.read_text()) or {}
        except yaml.YAMLError:
            doc = {}
        for cfg in doc.values():
            if isinstance(cfg, dict) and "base" in (cfg.get("outputs") or {}):
                return False
    write_profiles(project_dir, project or Path(project_dir).name)
    return True


# --------------------------------------------------------------- baseline --
def capture_baseline(project_dir: Path, rebuild: bool = True) -> tuple[Path, list[str]]:
    """Materialise the current code into the `base` target, and keep its artefacts.

    This is a **build**, not a copy, and that is the whole correctness of the
    tool. Copying `target/` aside produces a second manifest whose nodes resolve
    to the same relations as the first, so every value and profile diff compares
    a table with itself and reports clean — a false negative on every change.
    Building into the `base` target puts the comparison data in `base_*` schemas
    alongside the live `main_*` ones, which is what makes a diff a diff.

    `rebuild=False` re-captures artefacts only, for the case where the base
    schemas were built moments ago and the code has not moved since.
    """
    from pf.runtime.dbt_runtime import dbt

    src = dbt_dir(project_dir) / "target"
    if rebuild:
        # Here rather than only in the CI command: this is the function that
        # runs dbt, and `pf tool recce baseline` reaches it without passing
        # through `ci`. A checkout with packages declared and none installed
        # cannot compile, so the build fails before it materialises anything.
        ensure_packages(project_dir)
        env = dbt_env(project_dir)
        wh = env["PF_DUCKDB_PATH"]
        build = dbt(project_dir, "build", target="base", duckdb_path=wh)
        if build.returncode != 0:
            raise RuntimeError(
                "baseline build failed — the comparison environment would be "
                f"incomplete:\n{(build.stdout or build.stderr)[-2000:]}")
        # Column-level checks need a catalog. Failing to produce one degrades the
        # diff to structural checks rather than breaking it, so it is not fatal.
        dbt(project_dir, "docs", "generate", target="base", duckdb_path=wh)

    if not (src / "manifest.json").exists():
        raise FileNotFoundError(
            f"no dbt manifest at {src / 'manifest.json'} — run `pf seed` first")

    dst = baseline_dir(project_dir)
    dst.mkdir(parents=True, exist_ok=True)
    captured = []
    for name in BASELINE_ARTEFACTS:
        f = src / name
        if f.exists():
            shutil.copy2(f, dst / name)
            captured.append(name)
    return dst, captured


# ---------------------------------------------------------------- remote --
# Recce's half of the artefact store: which key an artefact belongs under, and
# why. `pf.artifacts` moves bytes and knows nothing about baselines; everything
# below is the semantics it deliberately does not have.
def baseline_prefix(group: str, project: str, ref: str = "") -> str:
    """Where a captured baseline lives, keyed by the ref it was built from."""
    base = artifacts.project_prefix(group, project)
    return f"{base}/transform/{BASELINE_DIR}/{artifacts.sanitize_ref(ref) if ref else artifacts.base_ref()}"


def review_prefix(group: str, project: str, ref: str = "") -> str:
    """Where a recorded review lives, keyed by the branch under review."""
    base = artifacts.project_prefix(group, project)
    return f"{base}/transform/{REVIEWS_DIR}/{artifacts.sanitize_ref(ref) if ref else artifacts.head_ref()}"


def baseline_pairs(project_dir: Path, group: str, project: str,
                   ref: str = "") -> list[tuple[str, Path]]:
    p = baseline_prefix(group, project, ref)
    return [(f"{p}/{name}", baseline_dir(project_dir) / name)
            for name in BASELINE_ARTEFACTS]


def review_pairs(project_dir: Path, group: str, project: str,
                 ref: str = "") -> list[tuple[str, Path]]:
    p = review_prefix(group, project, ref)
    return [(f"{p}/{STATE_FILE}", state_file(project_dir)),
            (f"{p}/{SUMMARY_FILE}", summary_file(project_dir))]


def _store(store: artifacts.Store | None) -> artifacts.Store | None:
    return store if store is not None else artifacts.Store.from_env()


def publish_baseline(project_dir: Path, group: str, project: str, ref: str = "",
                     store: artifacts.Store | None = None) -> list[artifacts.Transfer]:
    """Push the captured baseline. No store configured → nothing happens.

    Silent no-op rather than an error, in every publish and fetch below: a
    developer diffing against a baseline they built ten seconds ago has no use
    for a bucket, and making them configure one to run `pf tool recce baseline`
    would be a tax on the local-first path this platform is built around.
    """
    s = _store(store)
    return artifacts.push_files(s, baseline_pairs(project_dir, group, project, ref)) if s else []


def fetch_baseline(project_dir: Path, group: str, project: str, ref: str = "",
                   store: artifacts.Store | None = None) -> list[artifacts.Transfer]:
    """Pull the baseline for this ref into `transform/target-base/`."""
    s = _store(store)
    return artifacts.pull_files(s, baseline_pairs(project_dir, group, project, ref)) if s else []


def publish_review(project_dir: Path, group: str, project: str, ref: str = "",
                   store: artifacts.Store | None = None) -> list[artifacts.Transfer]:
    """Push the recorded review — the state file and the human-readable summary."""
    s = _store(store)
    return artifacts.push_files(s, review_pairs(project_dir, group, project, ref)) if s else []


def fetch_review(project_dir: Path, group: str, project: str, ref: str = "",
                 store: artifacts.Store | None = None) -> list[artifacts.Transfer]:
    """Pull a recorded review so `pf ui` and `recce server` have one to render."""
    s = _store(store)
    return artifacts.pull_files(s, review_pairs(project_dir, group, project, ref)) if s else []


def ensure_baseline(project_dir: Path, group: str, project: str,
                    ref: str = "") -> str:
    """Get a baseline onto disk however possible. Returns how, for printing.

    Order matters and is not arbitrary. A baseline already on disk is used
    as-is — re-pulling would overwrite a developer's local capture with main's,
    silently changing what their next diff is measured against. Only when there
    is nothing local do we go to the bucket.
    """
    if has_baseline(project_dir):
        return "local"
    got = fetch_baseline(project_dir, group, project, ref)
    if not got:
        return ""
    if has_baseline(project_dir):
        names = ", ".join(t.path.name for t in got if t.ok)
        return f"pulled {baseline_prefix(group, project, ref)} ({names})"
    return ""


def project_ids(project_dir: Path) -> tuple[str, str]:
    """(group, project) from the path layout `groups/<group>/projects/<project>`.

    The Dagster asset and the UI reach these functions holding a directory and
    no ids, and re-deriving the convention at each call site is how one of them
    ends up disagreeing with the others.
    """
    d = Path(project_dir)
    return (d.parents[1].name if len(d.parents) >= 2 else ""), d.name


# -------------------------------------------------------------------- run --
def dbt_env(project_dir: Path) -> dict[str, str]:
    """Environment recce's embedded dbt needs to resolve this project's profile.

    Recce does not run `dbt` as a subprocess — it loads dbt's own config in
    process — so it inherits our `profiles.yml`, which reads the warehouse path
    from `PF_DUCKDB_PATH`. Without it every recce command dies in dbt's Jinja
    renderer with `Env var required but not provided`, which reads like a recce
    bug and is not one. `pf.runtime.dbt_runtime.dbt()` sets the same two
    variables for the same reason.
    """
    import os

    from pf.runtime.warehouse import Warehouse

    d = Path(project_dir)
    group, project = project_ids(d)
    wh = Warehouse.for_project(d, group, project)

    env = dict(os.environ)
    env.setdefault("DBT_TARGET", "dev")
    env["PF_DUCKDB_PATH"] = str(wh.path)
    # dbt's duckdb adapter opens the file but will not create the directory
    # holding it, and it never goes through `Warehouse.connect`, which would.
    wh.ensure_dir()
    return env


def ensure_packages(project_dir: Path) -> bool:
    """Install `packages.yml` when `dbt_packages/` is not there yet.

    dbt refuses to compile at all in that state — "found N package(s) specified
    in packages.yml, but only 0 installed" — and a fresh checkout is exactly
    that state. Every other caller reaches dbt through `pf seed`, which installs
    first; the CI entry point below is the one that does not.
    """
    from pf.runtime.dbt_runtime import deps

    d = dbt_dir(project_dir)
    if not any((d / f).exists() for f in ("packages.yml", "dependencies.yml")):
        return False
    installed = d / "dbt_packages"
    if installed.is_dir() and any(installed.iterdir()):
        return False
    deps(project_dir, duckdb_path=dbt_env(project_dir)["PF_DUCKDB_PATH"])
    return True


def ensure_current_manifest(project_dir: Path) -> bool:
    """Parse this branch's dbt project so there is a *current* side to diff.

    Recce compares `target/` against `target-base/`. A committed baseline with
    no current artefacts — the normal state of a CI checkout — leaves the
    current side empty and recce exits with `Cannot load the manifest`.

    A parse, not a build: the manifest carries the schemas and the lineage,
    which is what the structural checks read, and it needs no warehouse.
    """
    from pf.runtime.dbt_runtime import parse

    if has_manifest(project_dir):
        return True
    parse(project_dir, duckdb_path=dbt_env(project_dir)["PF_DUCKDB_PATH"])
    return has_manifest(project_dir)


def _recce(project_dir: Path, *args: str, timeout: int = 900) -> subprocess.CompletedProcess:
    """Invoke the recce CLI with cwd set to the dbt project.

    cwd matters: recce resolves `target/`, `target-base/` and `recce.yml`
    relative to the dbt project directory, and passing --project-dir alone does
    not move the config lookup.
    """
    return subprocess.run(
        ["recce", *args], cwd=str(dbt_dir(project_dir)), env=dbt_env(project_dir),
        capture_output=True, text=True, timeout=timeout,
    )


def run(project_dir: Path, *, skip_query: bool = False) -> dict[str, Any]:
    """Run the preset checks headlessly. Returns a structured result.

    Never raises on a non-zero exit: a failing diff is a *finding*, and the
    caller (a Dagster asset, a CLI command) decides whether a finding should
    fail a run. Raising here would make "revenue moved" indistinguishable from
    "recce is not installed".
    """
    args = ["run", "--output", STATE_FILE, "--summary", SUMMARY_FILE]
    if skip_query:
        args.append("--skip-query")
    try:
        proc = _recce(project_dir, *args)
    except FileNotFoundError:
        return {"ok": False, "reason": "not_installed",
                "message": "recce is not on PATH — `uv sync --extra recce`"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "reason": "timeout", "message": "recce run timed out"}

    result: dict[str, Any] = {
        "ok": proc.returncode == 0,
        "reason": "" if proc.returncode == 0 else "checks_failed",
        "returncode": proc.returncode,
        "message": (proc.stderr or proc.stdout or "")[-2000:],
        "state_file": str(state_file(project_dir)),
    }
    result.update(read_state(project_dir))
    summary = summary_file(project_dir)
    if summary.exists():
        result["summary_markdown"] = summary.read_text()[:20000]
    return result


def read_state(project_dir: Path) -> dict[str, Any]:
    """Check counts from recce_state.json, or empty if it was never written."""
    p = state_file(project_dir)
    if not p.exists():
        return {}
    try:
        state = json.loads(p.read_text())
    except json.JSONDecodeError:
        return {}
    checks = state.get("checks") or []
    return {
        "checks_total": len(checks),
        "checks_named": [c.get("name", "?") for c in checks][:50],
        "generated_at": state.get("generated_at") or state.get("created_at") or "",
    }


def summary_markdown(project_dir: Path) -> str:
    p = summary_file(project_dir)
    return p.read_text() if p.exists() else ""


#: Which model a run was about. A recorded run carries its `check_id` and its
#: params, never a dbt node, so the model has to be recovered. `params.model` is
#: authoritative where recce takes one; the rest is the naming convention from
#: `build_checks` above, parsed back. Reading a string we wrote is safe in a way
#: that inferring a model from recce's compiled SQL is not — and the caller
#: validates every recovered name against a model list it already holds, so a
#: drift in the convention drops an attribution rather than inventing one.
_CHECK_MODEL_RE = re.compile(
    r"^(?:Value diff|Profile diff|Category drift) — ([A-Za-z0-9_]+)")


def _run_model(run: dict[str, Any], check: dict[str, Any]) -> str:
    explicit = ((run.get("params") or {}).get("model")
                or (check.get("params") or {}).get("model"))
    if explicit:
        return str(explicit)
    m = _CHECK_MODEL_RE.match(check.get("name") or "")
    return m.group(1) if m else ""


def model_diffs(project_dir: Path) -> dict[str, dict[str, Any]]:
    """What the recorded review measured, per dbt model.

    `read_state` counts checks; this says which model each one landed on and
    whether anything actually moved. The distinction a reviewer needs is
    three-way, not two: a model whose checks all came back empty is a different
    fact from one no check covered at all, and collapsing them into "no changes"
    reads as reassurance the review never gave.

    Empty when no review has been run — an unmeasured project, not a clean one.
    """
    p = state_file(project_dir)
    if not p.exists():
        return {}
    try:
        state = json.loads(p.read_text())
    except json.JSONDecodeError:
        return {}

    checks = {c.get("check_id"): c for c in state.get("checks") or []}
    out: dict[str, dict[str, Any]] = {}

    def row(name: str) -> dict[str, Any]:
        return out.setdefault(name, {
            "model": name, "checks": 0, "check_types": set(),
            "row_count": None, "rows_added": 0, "rows_removed": 0,
            "categories_drifted": [], "moved": False,
        })

    for run in state.get("runs") or []:
        kind = run.get("type") or ""
        check = checks.get(run.get("check_id")) or {}
        result = run.get("result")
        if not isinstance(result, dict):
            continue

        # row_count_diff is selector-driven: one run covers every modified table
        # and keys its result by model, so it attributes itself.
        if kind == "row_count_diff":
            for name, counts in result.items():
                if not isinstance(counts, dict):
                    continue
                r = row(name)
                r["checks"] += 1
                r["check_types"].add(kind)
                base, curr = counts.get("base"), counts.get("curr")
                if isinstance(base, int) and isinstance(curr, int):
                    r["row_count"] = {"base": base, "curr": curr,
                                      "delta": curr - base}
                    r["moved"] = r["moved"] or base != curr
            continue

        name = _run_model(run, check)
        if not name:
            continue
        r = row(name)
        r["checks"] += 1
        r["check_types"].add(kind)

        if kind == "value_diff":
            summary = result.get("summary") or {}
            added = int(summary.get("added") or 0)
            removed = int(summary.get("removed") or 0)
            r["rows_added"] += added
            r["rows_removed"] += removed
            r["moved"] = r["moved"] or bool(added or removed)
        elif kind == "query_diff":
            # A category drift returns *only* the rows that differ, so a
            # non-empty table is the drift itself.
            if (result.get("diff") or {}).get("data"):
                col = (check.get("name") or "").rpartition(".")[2]
                r["categories_drifted"].append(col or "?")
                r["moved"] = True

    for r in out.values():
        r["check_types"] = sorted(r["check_types"])
    return out


def check_results(project_dir: Path) -> list[dict[str, Any]]:
    """Every recorded check with its verdict — the validation itself, not a count.

    `read_state` says seventeen checks ran and `model_diffs` says which models
    moved. Neither answers the question a reviewer actually has, which is *what
    did this check find*. That detail was only ever visible by opening Recce's
    own UI, so a project whose server was not running showed a review with no
    findings in it.

    Each check reports `verdict`: `changed` when the comparison found a
    difference, `clean` when it ran and found none, `not_run` when it was
    recorded but never executed, and `errored` when it failed. Those are
    genuinely four outcomes and the earlier UI could distinguish none of them.
    """
    p = state_file(project_dir)
    if not p.exists():
        return []
    try:
        state = json.loads(p.read_text())
    except json.JSONDecodeError:
        return []

    runs_by_check: dict[str, dict[str, Any]] = {}
    for run in state.get("runs") or []:
        cid = run.get("check_id")
        if cid:
            runs_by_check[cid] = run

    out: list[dict[str, Any]] = []
    for check in state.get("checks") or []:
        cid = check.get("check_id")
        run = runs_by_check.get(cid) or {}
        kind = check.get("type") or run.get("type") or ""
        result = run.get("result") if isinstance(run.get("result"), dict) else None
        status = (run.get("status") or "").lower()

        verdict, detail = "not_run", "no run recorded for this check"
        if status and status not in {"finished", "successful", "success"}:
            verdict, detail = "errored", (run.get("error") or status)[:200]
        elif result is not None:
            verdict, detail = _verdict(kind, result, check)

        out.append({
            "name": check.get("name", "?"),
            "description": check.get("description", ""),
            "type": kind,
            "model": _run_model(run, check),
            "verdict": verdict,
            "detail": detail,
            "run_at": run.get("run_at", ""),
            "is_preset": bool(check.get("is_preset")),
        })
    # Findings first: a reviewer reads down until the differences run out.
    order = {"changed": 0, "errored": 1, "not_run": 2, "clean": 3}
    return sorted(out, key=lambda r: (order.get(r["verdict"], 9), r["name"]))


def _verdict(kind: str, result: dict[str, Any],
             check: dict[str, Any]) -> tuple[str, str]:
    """Turn one recorded result into (verdict, human detail)."""
    if kind == "row_count_diff":
        moved = [f"{n}: {c.get('base')} → {c.get('curr')}"
                 for n, c in result.items()
                 if isinstance(c, dict) and c.get("base") != c.get("curr")]
        if moved:
            return "changed", "; ".join(moved[:6])
        return "clean", f"{len(result)} model(s), row counts unchanged"

    if kind == "value_diff":
        s = result.get("summary") or {}
        added, removed = int(s.get("added") or 0), int(s.get("removed") or 0)
        total = s.get("total")
        if added or removed:
            return "changed", f"+{added} / −{removed} of {total} row(s)"
        return "clean", f"{total} row(s) compared, none added or removed"

    if kind == "query_diff":
        rows = (result.get("diff") or {}).get("data") or []
        col = (check.get("name") or "").rpartition(".")[2]
        if rows:
            return "changed", f"{len(rows)} value(s) differ in {col or 'result'}"
        return "clean", f"no drift in {col or 'result'}"

    if kind == "schema_diff":
        # Recce reports schema differences per node; any payload at all is a
        # finding, since an unchanged schema returns nothing to report.
        changed = [k for k, v in result.items() if v]
        if changed:
            return "changed", f"{len(changed)} model(s) changed shape"
        return "clean", "no column added, removed or retyped"

    if kind == "profile_diff":
        base = (result.get("base") or {}).get("data") or []
        curr = (result.get("current") or {}).get("data") or []
        if base != curr:
            return "changed", "distribution moved"
        return "clean", "distribution unchanged"

    return ("changed" if result else "clean"), ""


# ------------------------------------------------------------------ serve --
def server_argv(project_dir: Path, port: int = DEFAULT_PORT,
                host: str = "127.0.0.1") -> list[str]:
    """argv for `recce server`, review mode when a state file exists.

    Review mode opens the recorded state instead of recomputing, so the UI shows
    the same numbers the Dagster run reported. Serving a live re-diff would let
    the dashboard and the run disagree, and then neither is trusted.

    The state file is positional. `--state-file` is a plausible spelling recce
    does not have — it exits non-zero on the unknown option, so the server never
    came up and the control plane's embed had nothing to show.
    """
    argv = ["recce", "server", "--host", host, "--port", str(port)]
    if state_file(project_dir).exists():
        argv += ["--review", STATE_FILE]
    return argv


# --------------------------------------------------------------- bootstrap --
def bootstrap_project(root: Path, group: str, project: str,
                      project_dir: Path, config: dict[str, Any]) -> Any:
    """Idempotent per-project setup. Called by `pf bootstrap`.

    Tolerant of an empty project by contract — a freshly scaffolded entity has
    no dbt project at all, and bootstrapping it must still succeed.
    """
    from pf.scaffold.bootstrap import StepResult

    if not (dbt_dir(project_dir) / "dbt_project.yml").exists():
        return StepResult("recce", "skipped", "no dbt project")

    ensure_base_target(project_dir, project)
    _, changed = write_config(project_dir)
    n = len(generate_config(project_dir)["checks"])
    detail = f"{n} preset check(s)" + ("" if changed else ", unchanged")
    if not has_baseline(project_dir):
        # Not a failure. A project that has never captured a baseline is one
        # command away from working, and `pf bootstrap` reporting it as broken
        # would make every fresh project look red.
        detail += " · no baseline yet (`pf tool recce baseline`)"
    return StepResult("recce", "ok", detail)


# ----------------------------------------------------------------- dagster --
def dagster_assets(ctx: ToolContext) -> ToolContribution:
    """One `recce_review` asset, downstream of the marts it reviews.

    Deps are the project's mart models rather than the whole dbt graph: the
    review is about what a change did to the numbers people read, and hanging it
    off staging would rerun it for every raw-column rename.

    Emits nothing when there is no manifest — the same policy the dbt assets
    follow, and for the same reason: an asset with no lineage is a node that
    tells you nothing.
    """
    from dagster import AssetKey, MetadataValue, asset

    project_dir = Path(ctx.project_dir)
    if not has_manifest(project_dir):
        return ToolContribution()

    prefix = ctx.project.replace("-", "_")
    deps = [AssetKey([prefix, name]) for name in _mart_models(project_dir)]
    port = int(ctx.config.get("port", DEFAULT_PORT))

    @asset(
        name="recce_review",
        key_prefix=[prefix],
        group_name="review",
        deps=deps,
        description="dbt diff against the captured baseline. Structural blast "
                    "radius is `pf impact`; this is what actually moved.",
        compute_kind="recce",
        metadata={"dagster/kind": "recce", "tool": "recce"},
    )
    def _recce_review(context) -> None:  # noqa: ANN001 — see dagster_runtime note
        try:
            source = ensure_baseline(project_dir, ctx.group, ctx.project)
        except artifacts.ArtifactStoreError as exc:
            context.log.warning("artefact store unreachable: %s", exc)
            source = ""
        if source and source != "local":
            context.log.info("baseline %s", source)

        if not has_baseline(project_dir):
            context.log.warning(
                "no baseline on disk or in the artefact store — run "
                "`pf tool recce baseline %s %s` after a known-good build. "
                "Skipping the diff rather than comparing against nothing.",
                ctx.group, ctx.project)
            context.add_output_metadata({"status": "no_baseline"})
            return

        result = run(project_dir)
        md = result.get("summary_markdown") or "_no summary produced_"
        meta: dict[str, Any] = {
            "status": "ok" if result.get("ok") else result.get("reason", "failed"),
            "checks": result.get("checks_total", 0),
            "summary": MetadataValue.md(md),
            # The deep link is how the Recce UI is reachable from Dagster. See
            # the note in pf/tools/__init__.py on why this is a link rather than
            # an embedded tab.
            "recce_ui": MetadataValue.url(f"http://127.0.0.1:{port}/"),
            "state_file": result.get("state_file", ""),
        }
        if not result.get("ok") and result.get("reason") == "not_installed":
            context.log.warning(result.get("message", ""))
        # Published, not committed: the state file is where every reader of this
        # run looks next, and a Dagster run that leaves it on the daemon's disk
        # is a review nobody else can open.
        try:
            keys = [t.key for t in publish_review(project_dir, ctx.group, ctx.project)]
            if keys:
                meta["published"] = ", ".join(keys)
        except artifacts.ArtifactStoreError as exc:
            context.log.warning("review not published: %s", exc)
        context.add_output_metadata(meta)

    return ToolContribution(
        assets=[_recce_review],
        metadata={"recce_url": f"http://127.0.0.1:{port}/"},
    )


def _mart_models(project_dir: Path) -> list[str]:
    """Mart model names from the dbt manifest."""
    p = dbt_dir(project_dir) / "target" / "manifest.json"
    try:
        manifest = json.loads(p.read_text())
    except Exception:  # noqa: BLE001
        return []
    out = []
    for node in (manifest.get("nodes") or {}).values():
        if node.get("resource_type") != "model":
            continue
        if (node.get("path") or "").split("/")[0] == "marts":
            out.append(node["name"])
    return sorted(out)


# ------------------------------------------------------------- capability --
RECCE_DOCS = """\
# Recce — dbt review for {{group}}/{{project}}

`pf impact` says what *could* break. Recce says what *did* change.

## The loop

```bash
pf seed {{group}} {{project}}                 # build green
pf tool recce baseline {{group}} {{project}}  # capture that build as the baseline
#   ... change a model ...
pf seed {{group}} {{project}}
pf tool recce run {{group}} {{project}}       # diff against the baseline
pf tool recce serve {{group}} {{project}}     # read it in the Recce UI
```

## What is generated

`transform/recce.yml` is derived from `contracts/annotations.yaml` — a
`natural_key` role becomes a value-diff primary key, a `money_amount` becomes a
profile diff. **Edit the roles, not the config**; `pf bootstrap` regenerates it.

`transform/recce_state.json` and `transform/target-base/` are build artefacts.
Both are gate-denied for the same reason `target/` is: hand-editing a recorded
diff makes the review lie.

## Where the artefacts live

Not in git — in the artefact store (`docs/ARTIFACTS.md`). The baseline is
published under the ref it was built from and pulled by anything diffing
against that ref; the recorded review is published under the branch under
review. The commands above do both without being asked.

```bash
pf artifacts status                          # is a store configured, and reachable
pf artifacts pull {{group}} {{project}}      # baseline + review onto this machine
pf artifacts ls {{group}} {{project}}        # what has been published
```

With no store configured everything stays local, which is the right behaviour
on a laptop that built its own baseline ten seconds ago. In CI it is not: a
runner has code and no warehouse, so an unconfigured store there means the
review reports *not exercised* rather than green. Set the two secrets named in
`docs/ARTIFACTS.md`.

## In Dagster

The `recce_review` asset runs downstream of this project's marts and attaches the
diff summary plus a link to the Recce UI to the run. Dagster OSS has no
custom-tab extension point, so the single-pane view lives in `pf ui` →
**Review**, which embeds Recce beside the lineage this platform already tracks.

## Read it against the semantic layer

`pf ui` → **Workspace** joins this review to the MDL manifest on the model, so a
recorded diff is read as *which published entity moved and what it carries*
rather than as a list of dbt node names. It needs the `wren` tool on as well;
both are on by default for a new group.
"""

RECCE_JOB = """\
  # dbt review: what the change did to the data, not just to the DAG.
  #
  # Two upstream pieces, both pinned as submodules under vendor/recce:
  #   DataRecce/PR-Update  keeps the branch merged with its base, so the diff is
  #                        against current code rather than against something the
  #                        base branch already replaced
  #   DataRecce/recce      runs the preset checks and writes the summary
  #
  # autoMerge is deliberately false. A merge is a write to someone's branch, and
  # the platform's rule is that automation reports while a human merges.
  #
  # The baseline is *pulled*, not checked out. It used to travel in the repo;
  # that stopped scaling at 30 MB per project, so `pf tool recce ci` fetches it
  # from the artefact store, keyed by this PR's base branch, and pushes the
  # recorded review back under the head branch. Without the two secrets below
  # the job still runs — it just cannot find a baseline, and reports the review
  # as not exercised rather than failing.
  recce:
    needs: changes
    if: needs.changes.outputs.transform == 'true'
    runs-on: ubuntu-latest
    env:
      PF_ARTIFACTS_ACCESS_KEY_ID: ${{ secrets.PF_ARTIFACTS_ACCESS_KEY_ID }}
      PF_ARTIFACTS_SECRET_ACCESS_KEY: ${{ secrets.PF_ARTIFACTS_SECRET_ACCESS_KEY }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Check the branch contains its base
        uses: DataRecce/PR-Update@main
        with:
          autoMerge: 'false'

      - uses: astral-sh/setup-uv@v5
      - run: uv sync --extra recce --extra artifacts

      - name: Diff against the base build
        run: uv run pf tool recce ci {{group}} {{project}}

      - name: Publish the summary
        if: always()
        run: |
          F=groups/{{group}}/projects/{{project}}/transform/recce_summary.md
          [ -f "$F" ] && cat "$F" >> $GITHUB_STEP_SUMMARY || echo "no summary" >> $GITHUB_STEP_SUMMARY
"""

# Refreshing a published baseline is deliberately *not* a CI job here. It wants
# a `push` trigger, and the generated workflow is `pull_request`-only: its
# `changes` job diffs against `github.base_ref`, which a push does not have, so
# adding the trigger means reworking the guard every other job depends on. That
# is a change to `pf.scaffold.ci`, not to this tool.
#
# Nothing regresses by leaving it out. A baseline is refreshed by running
# `pf tool recce baseline` on the trunk, which now publishes instead of asking
# for a commit — the same manual cadence as before, one step shorter. The
# staleness that cadence allows is worth naming though: a baseline pulled by
# every PR and refreshed by nobody drifts one commit further from main on each
# merge, and the diffs stay green because the comparison state no longer exists
# rather than because nothing moved. That was equally true of the committed
# baselines; the store does not fix it and does not worsen it.

CAPABILITY = Capability(
    name="recce",
    description="dbt PR review: diff a change against a captured baseline.",
    files={"docs/recce.md": RECCE_DOCS},
    ci_jobs={"recce": RECCE_JOB},
    # The artefact store's credentials. Declared here rather than on a store
    # capability of its own because recce is what needs them: `pf capability`
    # lists the pair as missing on a machine that has not set them, which is the
    # question someone asks after their first "review not exercised".
    env=("PF_ARTIFACTS_ACCESS_KEY_ID", "PF_ARTIFACTS_SECRET_ACCESS_KEY"),
    settings={
        "permissions": {"allow": [
            "Bash(pf tool recce:*)", "Bash(pf artifacts:*)",
            "Bash(recce run:*)", "Bash(recce server:*)", "Bash(recce debug:*)",
        ]},
    },
    gate={
        # Recorded diff state and the captured baseline. Both are build
        # artefacts; editing either makes the review report something that never
        # happened. `**/target/**` does not cover `target-base`, since fnmatch
        # matches whole path segments.
        "denylist": [
            "**/transform/recce_state.json",
            "**/transform/recce_summary.md",
            "**/transform/target-base/**",
        ],
        # The config is generated from the ontology roles, so a hand edit is a
        # silent fork from the declaration everything else reads.
        "impact_required": ["**/transform/recce.yml"],
    },
)


# ------------------------------------------------------------------- tool --
TOOL = Tool(
    name="recce",
    title="Recce",
    summary="dbt PR review — diff a change against a captured baseline.",
    url="https://github.com/DataRecce/recce",
    # Enabled once for a family, inherited by every sister. "We review dbt
    # changes with Recce" is a group decision; sisters differ in business logic,
    # not in whether their numbers get checked.
    scope=frozenset({"project", "group"}),
    capability=CAPABILITY,
    default_enabled=True,
    requires=(
        Requirement("python", "recce", "uv sync --extra recce"),
        Requirement("binary", "recce", "uv sync --extra recce"),
    ),
    dbt=DbtBinding(
        needs_manifest=True,
        needs_baseline=True,
        baseline_dir=BASELINE_DIR,
        config_file=CONFIG_FILE,
        artefacts=(f"transform/{STATE_FILE}", f"transform/{SUMMARY_FILE}",
                   f"transform/{BASELINE_DIR}"),
    ),
    surface=Surface(
        port=DEFAULT_PORT,
        path="/",
        embeddable=True,
        start=("recce", "server", "--host", "127.0.0.1", "--port", "{port}"),
    ),
    bootstrap="pf.tools.recce:bootstrap_project",
    dagster="pf.tools.recce:dagster_assets",
    commands="pf.tools.recce:register_commands",
    stack_layer={
        "layer": "review", "title": "Review (Recce)", "upstream": "recce",
        "toolkits": ["recce-review"],
        "artefacts": "transform/recce.yml", "node_kinds": [],
    },
)


# -------------------------------------------------------------------- cli --
def register_commands(app: Any) -> None:
    """Attach `pf tool recce ...`. Imported lazily by the CLI, never at startup."""
    import typer
    from rich.console import Console

    console = Console()
    recce_app = typer.Typer(help="Recce: dbt review against a captured baseline.")

    def _pdir(group: str, project: str) -> Path:
        from pf.cli import pdir
        return pdir(group, project)

    def _baseline(d: Path, group: str, project: str) -> None:
        """Report where the baseline came from, and never fail the command over it.

        Every caller below can still do something useful without the store —
        diff against a local capture, serve a review that is already on disk —
        so a store that is configured but unreachable is a warning here. The one
        exception is `cmd_ci`, which handles it itself because there the
        fallback silently changes what the diff is measured against.
        """
        try:
            source = ensure_baseline(d, group, project)
        except artifacts.ArtifactStoreError as exc:
            console.print(f"[yellow]![/] artefact store: {exc}")
            return
        if source and source != "local":
            console.print(f"[dim]{source}[/]")

    def _published(kind: str, moved: list[artifacts.Transfer]) -> None:
        """Report what went to the bucket, or say nothing if there is no bucket."""
        for t in moved:
            console.print(f"  [dim]↑ {t.key} ({artifacts.human(t.size)})[/]")
        if not moved and artifacts.Store.from_env() is None:
            console.print(f"  [dim]{kind} kept local — no artefact store "
                          f"configured (`pf artifacts status`)[/]")

    @recce_app.command("baseline")
    def cmd_baseline(group: str, project: str,
                     ref: str = typer.Option("", "--ref",
                                             help="publish under this ref instead of the base branch"),
                     no_publish: bool = typer.Option(False, "--no-publish",
                                                     help="capture locally, do not upload")) -> None:
        """Capture the current dbt build as the comparison baseline, and publish it."""
        d = _pdir(group, project)
        try:
            dst, captured = capture_baseline(d)
        except FileNotFoundError as exc:
            console.print(f"[red]{exc}[/]")
            raise typer.Exit(1)
        console.print(f"[green]✓[/] baseline → {dst}")
        console.print(f"  captured: {', '.join(captured)}")
        if "catalog.json" not in captured:
            console.print("  [yellow]![/] no catalog.json — column-level checks "
                          "need `dbt docs generate`")
        if no_publish:
            return
        try:
            _published("baseline", publish_baseline(d, group, project, ref))
        except artifacts.ArtifactStoreError as exc:
            # A captured baseline that failed to upload is still a captured
            # baseline. Warn and exit 0 — failing here would make a network
            # blip look like a failed build.
            console.print(f"  [yellow]![/] not published: {exc}")

    @recce_app.command("config")
    def cmd_config(group: str, project: str) -> None:
        """Regenerate recce.yml from the project's ontology roles."""
        d = _pdir(group, project)
        path, changed = write_config(d)
        n = len(generate_config(d)["checks"])
        console.print(f"[green]✓[/] {path} — {n} check(s)"
                      + ("" if changed else " [dim](unchanged)[/]"))

    @recce_app.command("run")
    def cmd_run(group: str, project: str,
                strict: bool = typer.Option(False, "--strict",
                                            help="exit non-zero if a check fails")) -> None:
        """Run the preset checks against the baseline."""
        d = _pdir(group, project)
        _baseline(d, group, project)
        if not has_baseline(d):
            console.print("[red]no baseline[/] — run `pf tool recce baseline` "
                          "after a known-good build, or `pf artifacts pull "
                          f"{group} {project}` if one was published")
            raise typer.Exit(1)
        result = run(d)
        if result.get("reason") == "not_installed":
            console.print(f"[yellow]{result['message']}[/]")
            raise typer.Exit(1)
        mark = "[green]✓[/]" if result.get("ok") else "[yellow]![/]"
        console.print(f"{mark} {result.get('checks_total', 0)} check(s) — "
                      f"{result.get('state_file', '')}")
        try:
            _published("review", publish_review(d, group, project))
        except artifacts.ArtifactStoreError as exc:
            console.print(f"  [yellow]![/] not published: {exc}")
        if result.get("summary_markdown"):
            console.print(result["summary_markdown"][:4000])
        raise typer.Exit(1 if strict and not result.get("ok") else 0)

    @recce_app.command("serve")
    def cmd_serve(group: str, project: str,
                  port: int = typer.Option(DEFAULT_PORT),
                  host: str = typer.Option(
                      "127.0.0.1",
                      help="Bind address. The stack's front door proxies to "
                           "127.0.0.1; a container that publishes the port "
                           "directly needs 0.0.0.0.")) -> None:
        """Serve the Recce UI for this project."""
        import os
        d = _pdir(group, project)
        # The server renders artefacts; it does not produce them. A checkout
        # that has never run a review has neither, and since neither is in git
        # any more, "no bucket and nothing local" is the state to be loud about
        # rather than to serve an empty UI over.
        _baseline(d, group, project)
        if not state_file(d).exists():
            try:
                for t in fetch_review(d, group, project):
                    if t.ok:
                        console.print(f"[dim]↓ {t.key} ({artifacts.human(t.size)})[/]")
            except artifacts.ArtifactStoreError as exc:
                console.print(f"[yellow]![/] could not fetch the review: {exc}")
        if not state_file(d).exists():
            console.print("[yellow]![/] no recorded review on disk or in the "
                          f"store — `pf tool recce run {group} {project}` first")
        argv = server_argv(d, port=port, host=host)
        console.print(f"[dim]{' '.join(argv)}  (cwd={dbt_dir(d)})[/]")
        console.print(f"[green]→[/] http://{host}:{port}/")
        # execvpe, not execvp: the server loads dbt's config in process and needs
        # the same warehouse env every other recce invocation does.
        os.chdir(dbt_dir(d))
        os.execvpe(argv[0], argv, dbt_env(d))

    def _publish_ci_review(d: Path, group: str, project: str) -> None:
        """Upload the review, and never change the job's verdict by doing so.

        Called on both of `cmd_ci`'s exits, including the "not exercised" one —
        a review that could not run is still the record of this branch, and a
        reader looking for it in the bucket should find that sentence rather
        than the previous branch's numbers.
        """
        try:
            for t in publish_review(d, group, project):
                console.print(f"[dim]↑ {t.key} ({artifacts.human(t.size)})[/]")
        except artifacts.ArtifactStoreError as exc:
            console.print(f"[yellow]![/] review not published: {exc}")

    @recce_app.command("ci")
    def cmd_ci(group: str, project: str) -> None:
        """Baseline if absent, then diff. What the generated workflow runs.

        A CI checkout is code with no warehouse behind it, so this degrades in
        three steps rather than failing: the baseline is pulled from the
        artefact store, since it is no longer in the checkout; without data the
        value-level checks are skipped and the structural ones still run;
        without a baseline *and* without data there is nothing to compare and
        the run says so. A review that could not be exercised is a finding for
        the reader, not a red cross on a branch that did nothing wrong.
        """
        d = _pdir(group, project)
        ensure_packages(d)
        data = has_data(d)

        try:
            source = ensure_baseline(d, group, project)
        except artifacts.ArtifactStoreError as exc:
            # Reachable store, unusable answer. Say so plainly: the fallback
            # below builds a baseline from *this branch*, and a diff against
            # yourself reports clean, so an unexplained pull failure would read
            # as a green review.
            console.print(f"[yellow]![/] artefact store unreachable: {exc}")
            source = ""
        if source and source != "local":
            console.print(f"[dim]{source}[/]")

        if not has_baseline(d):
            if not data:
                console.print("[yellow]no baseline, and no warehouse to build "
                              "one from — review not exercised[/]")
                summary_file(d).write_text(
                    f"## recce — {group}/{project}\n\n"
                    "**Not exercised.** No baseline was found for this project — "
                    f"neither on disk (`transform/{BASELINE_DIR}/manifest.json`) "
                    f"nor in the artefact store under `{baseline_prefix(group, project)}` "
                    "— and there is no warehouse here to build one from, so there "
                    "was nothing to compare this branch against.\n\n"
                    "Run `pf seed` and then `pf tool recce baseline "
                    f"{group} {project}` on a known-good build of the base "
                    "branch. That publishes the baseline this job pulls.\n"
                )
                _publish_ci_review(d, group, project)
                raise typer.Exit(0)
            console.print("[yellow]no baseline — capturing the current build[/]")
            try:
                capture_baseline(d)
            except (FileNotFoundError, RuntimeError) as exc:
                console.print(f"[red]{exc}[/]")
                raise typer.Exit(1)

        if not ensure_current_manifest(d):
            console.print("[red]dbt parse produced no manifest — this branch's "
                          "dbt project does not compile[/]")
            raise typer.Exit(1)

        result = run(d, skip_query=not data)
        # Same as `pf tool recce run`: a missing recce is a broken environment,
        # not a failed review, and "0 check(s), ok=False" says neither.
        if result.get("reason") == "not_installed":
            console.print(f"[red]{result['message']}[/]")
            raise typer.Exit(1)
        # Parenthesised, not bracketed: Rich reads `[...]` as a style tag and
        # would swallow the scope instead of printing it.
        scope = "full" if data else "structural only — no warehouse"
        console.print(f"{result.get('checks_total', 0)} check(s) ({scope}), "
                      f"ok={result.get('ok')}")
        _publish_ci_review(d, group, project)
        raise typer.Exit(0 if result.get("ok") else 1)

    app.add_typer(recce_app, name="recce")
