"""Read an existing repository and report what it is made of.

Everything here is *observation only*. Nothing is decided and nothing is written,
because the decisions depend on facts the survey has to establish first — which
layer convention the models use, whether an orchestrator is present, which of our
capabilities the repo already solves for itself.

Detection is deliberately conservative. A false positive here becomes a silent
mistranslation later: claiming a repo "already has" a capability means we skip
wiring ours in, and the project ships without it. So each check looks for the
thing itself rather than for something correlated with it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

# Incoming layer name -> ours. Repos disagree about this more than about almost
# anything else, and the three families below cover nearly all of them.
LAYER_MAP = {
    "staging": "staging", "stg": "staging", "raw": "staging", "base": "staging",
    "bronze": "staging", "sources": "staging",
    "intermediate": "marts", "int": "marts", "silver": "marts",
    "marts": "marts", "mart": "marts", "core": "marts", "gold": "marts",
    "facts": "marts", "dimensions": "marts", "dim": "marts", "fct": "marts",
    "semantic": "semantic", "metrics": "semantic", "semantic_models": "semantic",
    "utils": "utils", "utilities": "utils", "util": "utils",
}

# Import markers. Matched against source text rather than filenames: a `dags/`
# directory is a convention, `from airflow import DAG` is a fact.
ORCHESTRATOR_MARKERS = {
    "airflow": re.compile(r"^\s*(?:from|import)\s+airflow\b", re.M),
    "prefect": re.compile(r"^\s*(?:from|import)\s+prefect\b", re.M),
    "dagster": re.compile(r"^\s*(?:from|import)\s+dagster\b", re.M),
}

INGESTION_MARKERS = {
    "dlt": re.compile(r"^\s*(?:from|import)\s+dlt\b", re.M),
    "airbyte": re.compile(r"airbyte", re.I),
    "fivetran": re.compile(r"fivetran", re.I),
    "singer": re.compile(r"^\s*(?:from|import)\s+singer\b", re.M),
}

WAREHOUSES = ("duckdb", "snowflake", "bigquery", "redshift", "postgres",
              "databricks", "athena", "trino", "motherduck")

SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", "target",
             "dbt_packages", ".dbt", "logs", ".mypy_cache", ".ruff_cache"}


@dataclass
class Survey:
    """What an incoming repository contains."""

    root: Path
    dbt_project: Path | None = None
    dbt_name: str = ""
    #: our layer -> the model files that map into it, with their path *below*
    #: the incoming layer directory preserved
    models: dict[str, list[Path]] = field(default_factory=dict)
    #: incoming layer directory name -> ours, for the report
    layer_mapping: dict[str, str] = field(default_factory=dict)
    unmapped_layers: list[str] = field(default_factory=list)
    macros: list[Path] = field(default_factory=list)
    seeds: list[Path] = field(default_factory=list)
    tests: list[Path] = field(default_factory=list)
    packages: Path | None = None
    profiles: Path | None = None
    warehouses: set[str] = field(default_factory=set)
    orchestrators: set[str] = field(default_factory=set)
    orchestration_files: list[Path] = field(default_factory=list)
    ingestion: set[str] = field(default_factory=set)
    capabilities_present: set[str] = field(default_factory=set)

    @property
    def model_count(self) -> int:
        return sum(len(v) for v in self.models.values())

    @property
    def needs_orchestrator_migration(self) -> bool:
        return bool(self.orchestrators - {"dagster"})


def _walk(root: Path, suffixes: tuple[str, ...]) -> list[Path]:
    out: list[Path] = []
    for p in root.rglob("*"):
        if p.is_dir() or p.suffix not in suffixes:
            continue
        if SKIP_DIRS & set(p.relative_to(root).parts):
            continue
        out.append(p)
    return out


def survey(root: Path) -> Survey:
    """Inspect a repository. Reads only; writes nothing."""
    s = Survey(root=root)

    dbt_projects = [p for p in root.rglob("dbt_project.yml")
                    if not SKIP_DIRS & set(p.relative_to(root).parts)]
    if dbt_projects:
        # The shallowest one. A repo with several is either a monorepo or has
        # vendored packages; the top-level project is the one being onboarded.
        s.dbt_project = min(dbt_projects, key=lambda p: len(p.parts))
        try:
            doc = yaml.safe_load(s.dbt_project.read_text()) or {}
            s.dbt_name = str(doc.get("name", ""))
        except yaml.YAMLError:
            pass
        _survey_dbt(s, s.dbt_project.parent)

    for path in _walk(root, (".py",)):
        text = path.read_text(errors="ignore")
        hits = {name for name, rx in ORCHESTRATOR_MARKERS.items() if rx.search(text)}
        if hits:
            s.orchestrators |= hits
            if hits - {"dagster"}:
                s.orchestration_files.append(path)
        s.ingestion |= {n for n, rx in INGESTION_MARKERS.items() if rx.search(text)}

    if (root / "prefect.yaml").exists():
        s.orchestrators.add("prefect")

    s.capabilities_present = _detect_capabilities(root)
    return s


def _survey_dbt(s: Survey, dbt_dir: Path) -> None:
    """Classify a dbt project's models into our layers."""
    models_dir = dbt_dir / "models"
    if models_dir.exists():
        for f in _walk(models_dir, (".sql", ".yml", ".yaml")):
            rel = f.relative_to(models_dir)
            top = rel.parts[0].lower() if len(rel.parts) > 1 else ""
            layer = LAYER_MAP.get(top)
            if layer is None:
                # An unrecognised top-level directory is kept, not dropped, and
                # reported. Guessing a layer for it would put models in a place
                # the semantic layer then reasons about wrongly.
                layer = "marts"
                if top and top not in s.unmapped_layers:
                    s.unmapped_layers.append(top)
            elif top:
                s.layer_mapping[top] = layer
            s.models.setdefault(layer, []).append(f)

    s.macros = _walk(dbt_dir / "macros", (".sql",)) if (dbt_dir / "macros").exists() else []
    s.seeds = _walk(dbt_dir / "seeds", (".csv",)) if (dbt_dir / "seeds").exists() else []
    s.tests = _walk(dbt_dir / "tests", (".sql",)) if (dbt_dir / "tests").exists() else []

    if (dbt_dir / "packages.yml").exists():
        s.packages = dbt_dir / "packages.yml"

    for name in ("profiles.yml", "profiles.yaml"):
        if (dbt_dir / name).exists():
            s.profiles = dbt_dir / name
    if s.profiles is None:
        found = [p for p in s.root.rglob("profiles.yml")
                 if not SKIP_DIRS & set(p.relative_to(s.root).parts)]
        s.profiles = found[0] if found else None

    if s.profiles is not None:
        text = s.profiles.read_text(errors="ignore").lower()
        s.warehouses = {w for w in WAREHOUSES if re.search(rf"\b{w}\b", text)}


def _detect_capabilities(root: Path) -> set[str]:
    """Which of our capabilities this repo already solves for itself.

    Conservative on purpose. Reporting a capability as present means we do not
    wire ours in, so a loose match here ships a project without the thing it was
    supposed to get.
    """
    present: set[str] = set()

    workflows = root / ".github" / "workflows"
    if workflows.exists() and any(workflows.glob("*.y*ml")):
        present.add("github")

    # Evidence specifically, not "some BI directory" — a `reports/` folder full
    # of screenshots is not a reporting layer.
    for pkg in root.rglob("package.json"):
        if SKIP_DIRS & set(pkg.relative_to(root).parts):
            continue
        if "@evidence-dev" in pkg.read_text(errors="ignore"):
            present.add("evidence")
            break

    return present
