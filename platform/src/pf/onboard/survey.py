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
    "airflow": re.compile(r"^\s*(?:from|import)\s+airflow\b", re.MULTILINE),
    "prefect": re.compile(r"^\s*(?:from|import)\s+prefect\b", re.MULTILINE),
    "dagster": re.compile(r"^\s*(?:from|import)\s+dagster\b", re.MULTILINE),
}

INGESTION_MARKERS = {
    "dlt": re.compile(r"^\s*(?:from|import)\s+dlt\b", re.MULTILINE),
    "airbyte": re.compile(r"airbyte", re.IGNORECASE),
    "fivetran": re.compile(r"fivetran", re.IGNORECASE),
    "singer": re.compile(r"^\s*(?:from|import)\s+singer\b", re.MULTILINE),
}

WAREHOUSES = ("duckdb", "snowflake", "bigquery", "redshift", "postgres",
              "databricks", "athena", "trino", "motherduck")

SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", "target",
             "dbt_packages", ".dbt", "logs", ".mypy_cache", ".ruff_cache"}

#: Build output and vendored copies that look like project content. `target-base`
#: and friends are tool artefacts some repos check in; importing them ships a
#: stale manifest that `pf check` will later reason about as if it were current.
SKIP_DIR_PATTERNS = ("target-", "dbt_packages", ".dagster")

#: dbt built-ins a project may override. Overriding one is legitimate in the
#: repository it came from and wrong here, because the platform's own layout
#: depends on the default behaviour — so these are reported, never copied
#: silently. The value is what breaks, which is the part worth reading.
RESERVED_MACROS = {
    "generate_schema_name": (
        "decides which schema every model lands in. The platform relies on "
        "`+schema: staging` / `+schema: marts` for layer separation, and the "
        "common override collapses both into one schema on non-prod targets"),
    "generate_database_name": (
        "redirects models across databases; each project here owns exactly one"),
    "generate_alias_name": (
        "renames relations, which detaches model names from the knowledge graph"),
    "ref": "overriding ref rewires lineage, which the impact gate is derived from",
    "source": "overriding source rewires lineage at the point annotations attach",
}

#: dbt path key -> (dbt's default directory, the file suffixes worth collecting).
#:
#: Read from the source's own config rather than assumed, because a repo that
#: keeps its tests in `data-tests/` really has tests and scanning `tests/` finds
#: an empty directory. The contents are then copied into *this* platform's
#: standard layout — the source's paths are not carried across, or the merged
#: config would name directories the files were moved out of.
#:
#: Adding a collected path kind is one entry here and one in `Survey`.
COLLECTED_PATHS: dict[str, tuple[str, tuple[str, ...]]] = {
    "macro-paths": ("macros", (".sql",)),
    "seed-paths": ("seeds", (".csv",)),
    "test-paths": ("tests", (".sql",)),
    "snapshot-paths": ("snapshots", (".sql",)),
    "analysis-paths": ("analyses", (".sql",)),
}

#: Survey attribute for each collected path key.
_PATH_ATTR = {"macro-paths": "macros", "seed-paths": "seeds", "test-paths": "tests",
              "snapshot-paths": "snapshots", "analysis-paths": "analyses"}


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
    #: the source dbt_project.yml, parsed — path keys, vars and per-layer config
    dbt_config: dict = field(default_factory=dict)
    snapshots: list[Path] = field(default_factory=list)
    analyses: list[Path] = field(default_factory=list)
    #: macro stem -> file, for every macro the project defines
    macro_names: dict[str, Path] = field(default_factory=dict)
    #: the subset of those that override a dbt built-in
    reserved_macros: dict[str, Path] = field(default_factory=dict)
    #: declared package key -> call sites found in the project's own SQL
    package_usage: dict[str, int] = field(default_factory=dict)
    #: packages pinned to a moving git ref rather than a revision
    unpinned_packages: list[str] = field(default_factory=list)

    @property
    def model_count(self) -> int:
        return sum(len(v) for v in self.models.values())

    @property
    def sql_model_count(self) -> int:
        return sum(1 for v in self.models.values() for f in v if f.suffix == ".sql")

    @property
    def needs_orchestrator_migration(self) -> bool:
        return bool(self.orchestrators - {"dagster"})

    def sql_files(self) -> list[Path]:
        """Every SQL file whose dialect has to survive the move."""
        return [f for v in self.models.values() for f in v if f.suffix == ".sql"] \
            + self.macros + self.tests + self.snapshots + self.analyses


def is_build_artifact(parts: tuple[str, ...]) -> bool:
    """Whether a path lies under build output or a vendored copy.

    Shared with `pf dialect` so a standalone scan and an import scan agree. They
    disagreed once, over `target-base/`, and a tool that reports two different
    numbers for the same tree is a tool nobody checks twice.
    """
    if SKIP_DIRS & set(parts):
        return True
    return any(part.startswith(pat) for part in parts for pat in SKIP_DIR_PATTERNS)


def _walk(root: Path, suffixes: tuple[str, ...]) -> list[Path]:
    out: list[Path] = []
    for p in root.rglob("*"):
        if p.is_dir() or p.suffix not in suffixes:
            continue
        if is_build_artifact(p.relative_to(root).parts):
            continue
        out.append(p)
    return out


def _dirs_for(cfg: dict, key: str, default: str) -> list[str]:
    """A dbt path key, which may be a string or a list, with dbt's default."""
    raw = cfg.get(key) or default
    return [raw] if isinstance(raw, str) else [str(x) for x in raw]


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
            doc = yaml.safe_load(s.dbt_project.read_text(encoding="utf-8")) or {}
            s.dbt_name = str(doc.get("name", ""))
            s.dbt_config = doc if isinstance(doc, dict) else {}
        except yaml.YAMLError:
            pass
        _survey_dbt(s, s.dbt_project.parent)

    for path in _walk(root, (".py",)):
        text = path.read_text(errors="ignore", encoding="utf-8")
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


def _collect(dbt_dir: Path, cfg: dict, key: str, default: str,
             suffixes: tuple[str, ...]) -> list[Path]:
    """Files under whichever directories the project's own config names.

    Reading the path keys rather than assuming dbt's defaults is not pedantry: a
    project that sets `test-paths: ["data-tests"]` keeps real tests there, and
    scanning `tests/` finds an empty directory and reports zero. Silently
    importing a project minus its tests is exactly the kind of quiet loss that
    only surfaces when something breaks in production.
    """
    out: list[Path] = []
    for name in _dirs_for(cfg, key, default):
        d = dbt_dir / name
        if d.exists():
            out += _walk(d, suffixes)
    return out


def _survey_dbt(s: Survey, dbt_dir: Path) -> None:
    """Classify a dbt project's models into our layers."""
    cfg = s.dbt_config
    model_dirs = _dirs_for(cfg, "model-paths", "models")
    models_dir = dbt_dir / model_dirs[0]
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

    for key, (default, suffixes) in COLLECTED_PATHS.items():
        setattr(s, _PATH_ATTR[key], _collect(dbt_dir, cfg, key, default, suffixes))

    s.macro_names = {m.stem: m for m in s.macros}
    s.reserved_macros = {
        name: path for name, path in s.macro_names.items()
        if name in RESERVED_MACROS
    }

    if (dbt_dir / "packages.yml").exists():
        s.packages = dbt_dir / "packages.yml"
        _survey_packages(s)

    for name in ("profiles.yml", "profiles.yaml"):
        if (dbt_dir / name).exists():
            s.profiles = dbt_dir / name
    if s.profiles is None:
        found = [p for p in s.root.rglob("profiles.yml")
                 if not SKIP_DIRS & set(p.relative_to(s.root).parts)]
        s.profiles = found[0] if found else None

    if s.profiles is not None:
        text = s.profiles.read_text(errors="ignore", encoding="utf-8").lower()
        s.warehouses = {w for w in WAREHOUSES if re.search(rf"\b{w}\b", text)}


def _package_namespaces(entry: dict) -> tuple[str, list[str]]:
    """A package's declared key, and the Jinja namespaces it might be called by.

    dbt namespaces a package's macros under its *project* name, which is inside
    the package and not knowable from the declaration. The candidates below are
    a heuristic, so a zero count means "worth checking" and never "safe to
    delete" — the survey reports it and a human decides.
    """
    key = str(entry.get("package") or entry.get("git") or entry.get("local") or "")
    tail = key.rstrip("/").rsplit("/", 1)[-1]
    tail = re.sub(r"\.git$", "", tail)
    under = tail.replace("-", "_")
    stripped = re.sub(r"^dbt_", "", under)
    # `dbt-audit-helper` is imported as `audit_helper`, so the prefix has to come
    # off — but doing that to `dbt_date` leaves `date`, which matches every YAML
    # description ending in the word. Short candidates are dropped rather than
    # inflating the count with prose.
    candidates = {under} | ({stripped} if len(stripped) >= 6 else set())
    return key, sorted(c for c in candidates if c)


def _survey_packages(s: Survey) -> None:
    """Count what each declared package is actually used for, and how it is pinned."""
    try:
        entries = (yaml.safe_load(s.packages.read_text(encoding="utf-8")) or {}).get("packages") or []
    except yaml.YAMLError:
        return

    corpus = " ".join(
        f.read_text(errors="ignore", encoding="utf-8")
        for f in [*(x for v in s.models.values() for x in v), *s.macros, *s.tests]
    )

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        key, namespaces = _package_namespaces(entry)
        # A macro call or a generic test, not a bare word before a full stop.
        s.package_usage[key] = sum(
            len(re.findall(rf"\b{re.escape(ns)}\.[a-z_][a-z0-9_]*", corpus))
            for ns in namespaces)

        # A git package with no revision, or one pointed at a moving branch, is
        # not a pin. This repo treats upstream versions as a human decision, and
        # a floating `main` makes every build a different build.
        if "git" in entry:
            rev = str(entry.get("revision", "")).strip()
            if not rev or rev.lower() in {"main", "master", "head"}:
                s.unpinned_packages.append(f"{key} @ {rev or 'no revision'}")


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
        if "@evidence-dev" in pkg.read_text(errors="ignore", encoding="utf-8"):
            present.add("evidence")
            break

    return present
