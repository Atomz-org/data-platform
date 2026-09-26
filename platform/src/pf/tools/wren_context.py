"""One Wren workspace per project, generated from the semantic layer, and the
boundary every Wren call is made inside.

The platform already projects `mdl/mdl.json` for any MDL consumer. Current Wren
is more than a planner: its CLI keeps *context* (business rules for an LLM),
*memory* (questions already answered, as NL→SQL pairs) and *cubes*, and every
one of those commands looks for a project directory with a `wren_project.yml`.
This module writes that directory — `mdl/wren/` — from what the project already
knows, so nothing about the semantic layer is stated a second time:

    mdl/wren/
      wren_project.yml         name, catalog, schema, data source — from the manifest
      target/mdl.json          the manifest an LLM may see: restricted columns removed
      knowledge/rules/NN-*.md  what the ontology, metrics, policies and decisions say
      knowledge/sql/*.md       questions answered before, as `wren memory store` writes them
      .wren/memory/            the derived index, when the `memory` extra is installed

## The boundary

Wren defaults to `~/.wren` for its config, profiles and memory: one home for
every project on the machine, which is the exact thing multi-tenancy forbids.
Every call made through `run()` sets `WREN_PROJECT_HOME` and `WREN_HOME` to the
workspace, runs *in* the workspace, and passes the workspace's own memory path.
A question asked of one project cannot recall another project's answers, because
the process that answers it cannot see them.

## What an LLM may see

`isHidden` in the platform's manifest is the PII flag. A hidden column is still
*in* that manifest, because BI tools mask rather than drop. The copy written to
`target/mdl.json` drops it, along with any relationship that joins on it, any
cube measure or dimension that reads it and any view that names it — so the
model an agent plans against has no word for the column at all, and a plan that
names one fails in the planner rather than in a policy check afterwards.

## Generated, tracked, checked

`wren_project.yml` and the `NN-*.md` rules are tracked, like the OKF bundles,
because they are what a reviewer reads to know what an agent was told. They are
rebuilt from tracked inputs only (`mdl/mdl.json`, `kg/graph.json`, the
ontology), so `check()` gives the same answer on a runner with no warehouse as
on a laptop with one. Rules that do not match `NN-*.md` are a steward's own and
are never touched.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

WORKSPACE_REL = "mdl/wren"
PROJECT_FILE = "wren_project.yml"
TARGET_REL = "target/mdl.json"
RULES_REL = "knowledge/rules"
PAIRS_REL = "knowledge/sql"
MEMORY_REL = ".wren/memory"
#: Hand-written rules a group states once for every sister: `groups/<g>/wren/knowledge/rules/*.md`.
GROUP_RULES_REL = "wren/knowledge/rules"
SCHEMA_VERSION = 2
#: A role that names personal data never reaches the LLM-facing manifest,
#: whether or not the column was flagged.
RESTRICTED_ROLE_PREFIXES = ("pii_",)
#: The rules this module writes. Anything else under `knowledge/rules/` is a
#: steward's and is left alone.
GENERATED = re.compile(r"^\d\d-[\w-]+\.md$")
#: What a role means for aggregation, stated for the LLM in the words the
#: platform uses everywhere else. A role not listed is described by name only.
ROLE_NOTES = {
    "natural_key": "identity of the row; count it, never sum it",
    "foreign_key": "a join to another model along a declared relationship",
    "event_time": "the time axis; the default for any trend or period",
    "reference_date": "a date attribute, not the time axis",
    "money_amount": "additive within one currency; the sibling currency_code says which",
    "currency_code": "ISO 4217 code of the money columns beside it",
    "quantity": "additive count or volume; never money",
    "unit_price": ("a price per unit — never summed, never averaged across rows; "
                   "weight by quantity or take a ratio of additive parts"),
    "percentage": "already a ratio — never summed or averaged; recompute from its parts",
    "status_enum": "a fixed set of values; see the enumerations",
    "flag": "true/false; count the trues",
    "measure": "a number that may be aggregated as its metric says",
}


# ----------------------------------------------------------------- paths --
def workspace(project_dir: str | Path) -> Path:
    return Path(project_dir) / WORKSPACE_REL


def target_path(project_dir: str | Path) -> Path:
    return workspace(project_dir) / TARGET_REL


def exists(project_dir: str | Path) -> bool:
    return (workspace(project_dir) / PROJECT_FILE).is_file()


def installed() -> bool:
    return shutil.which("wren") is not None


def env_for(ws: Path) -> dict[str, str]:
    """Everything Wren would otherwise read from `~/.wren`, pointed inside."""
    ws = Path(ws)
    return {"WREN_PROJECT_HOME": str(ws), "WREN_HOME": str(ws / ".wren")}


def run(ws: Path, *args: str, timeout: int = 120) -> subprocess.CompletedProcess:
    """`wren <args>` inside the workspace and nowhere else."""
    ws = Path(ws)
    return subprocess.run(["wren", *args], cwd=str(ws), env={**os.environ, **env_for(ws)},
                          capture_output=True, text=True, timeout=timeout)


# ------------------------------------------------------------- redaction --
def _restricted(column: dict[str, Any], hide_roles: frozenset[str]) -> bool:
    props = column.get("properties") or {}
    role = str(props.get("pf.role") or "")
    return (bool(column.get("isHidden"))
            or str(props.get("pf.pii") or "").lower() == "true"
            or role.startswith(RESTRICTED_ROLE_PREFIXES)
            or role in hide_roles)


def _names(text: str, names: set[str]) -> bool:
    return any(re.search(rf"\b{re.escape(n)}\b", text) for n in names)


def redact(manifest: dict[str, Any],
           hide_roles: tuple[str, ...] | list[str] = ()) -> tuple[dict[str, Any], dict[str, list[str]]]:
    """The manifest an LLM may see, and what was taken out of it, per model.

    A column goes when it is hidden, flagged PII, carries a `pii_*` role, or a
    role the project's tool config lists under `hide_roles`. Everything that
    reads a removed column goes with it, so nothing left can name it.
    """
    hide = frozenset(hide_roles)
    out: dict[str, Any] = json.loads(json.dumps(manifest))
    hidden: dict[str, list[str]] = {}
    for model in out.get("models") or []:
        keep, gone = [], []
        for c in model.get("columns") or []:
            (gone if _restricted(c, hide) else keep).append(c)
        model["columns"] = keep
        if gone:
            hidden[str(model.get("name"))] = [str(c.get("name")) for c in gone]
    if not hidden:
        return out, hidden
    every = {c for cols in hidden.values() for c in cols}
    out["relationships"] = [
        r for r in out.get("relationships") or []
        if not any(_names(str(r.get("condition") or ""), {f"{m}.{c}" for c in cols})
                   for m, cols in hidden.items())
    ]
    for cube in out.get("cubes") or []:
        cols = set(hidden.get(str(cube.get("baseObject")), []))
        if not cols:
            continue
        cube["measures"] = [x for x in cube.get("measures") or [] if not _names(str(x.get("expression") or ""), cols)]
        for key in ("dimensions", "timeDimensions"):
            cube[key] = [d for d in cube.get(key) or [] if str(d.get("name")) not in cols]
    out["views"] = [v for v in out.get("views") or [] if not _names(str(v.get("statement") or ""), every)]
    return out, hidden


# ---------------------------------------------------------------- project --
def project_yaml(manifest: dict[str, Any], group: str, project: str) -> str:
    return (
        f"# GENERATED by `pf tool wren workspace {group} {project}` from mdl/mdl.json — never hand-edit.\n"
        f"schema_version: {SCHEMA_VERSION}\n"
        f"name: {group.replace('-', '_')}__{project.replace('-', '_')}\n"
        f"catalog: {manifest.get('catalog') or group.replace('-', '_')}\n"
        f"schema: {manifest.get('schema') or project.replace('-', '_')}\n"
        f"data_source: {str(manifest.get('dataSource') or 'duckdb').lower()}\n"
    )


# ------------------------------------------------------------------ rules --
def _one_line(text: Any) -> str:
    return " ".join(str(text or "").split())


def _table(header: list[str], rows: list[list[str]]) -> list[str]:
    cell = lambda s: _one_line(s).replace("|", "\\|")  # noqa: E731 — a local formatter
    return ["| " + " | ".join(header) + " |", "|" + "---|" * len(header),
            *("| " + " | ".join(cell(c) for c in r) + " |" for r in rows)]


def rules(root: str | Path, group: str, project: str, manifest: dict[str, Any],
          hidden: dict[str, list[str]] | None = None) -> dict[str, str]:
    """`knowledge/rules/NN-*.md`, from the project's own facts.

    Read through the OKF projection's gatherer, which already joins the manifest,
    the ontology and the tracked graph for the same purpose: telling a reader
    what a table and a metric mean. Two readers of the same facts, one gatherer.
    """
    from pf.projections import okf

    root = Path(root)
    facts = okf.gather(root, group, project)
    schema = manifest.get("schema") or project.replace("-", "_")
    cubes = [c for c in manifest.get("cubes") or [] if isinstance(c, dict)]
    models = [str(m.get("name")) for m in manifest.get("models") or []]
    out: dict[str, str] = {}

    # -- scope: the boundary, stated to the reader that has to respect it -----
    lines = [
        f"# Scope — groups/{group}/projects/{project}",
        "",
        f"This workspace is one project of the `{group}` group. Every model in it is a",
        f"mart of `{project}` (MDL catalog `{manifest.get('catalog') or group}`, schema `{schema}`),",
        "addressed by its model name; the engine maps that name to the project's own warehouse.",
        "",
        "- Answer only from the models, cubes and rules in this workspace. Another",
        "  project's tables are not visible here and are never guessed at or joined.",
        "- Columns that hold personal data are absent from this workspace by design.",
        "  A question that needs one has no answer here, and saying so is the answer.",
        "- Every query is planned through the MDL, dry-run, row-limited and recorded",
        "  before it runs. Write one `SELECT` over model names exactly as listed.",
        "- A governed number is its metric: answer it from the cube"
        + (f" `{cubes[0]['name']}`" if cubes else "")
        + " or from `query_metrics`, never by recomputing it in SQL.",
        "- A price is a unit price and a percentage is already a ratio: neither is",
        "  summed or averaged across rows. Money is additive within one currency.",
        "",
        "## Models",
        "",
        *(f"- `{m}`" for m in models),
    ]
    if hidden:
        lines += ["", "## Removed before you read this", "",
                  *(f"- `{m}`: {len(cols)} column(s) classified as personal data"
                    for m, cols in sorted(hidden.items()))]
    out["00-scope.md"] = "\n".join(lines) + "\n"

    # -- group rules: what the family says once, copied into every sister ------
    group_rules = root / "groups" / group / GROUP_RULES_REL
    if group_rules.is_dir():
        for p in sorted(group_rules.glob("*.md")):
            out[f"05-group-{p.stem}.md"] = p.read_text(encoding="utf-8")

    # -- concepts and roles ---------------------------------------------------
    concept_of = okf._concepts(facts) if facts.onto is not None else {}  # noqa: SLF001 — same facts, same reading
    rows = []
    for m in manifest.get("models") or []:
        name = str(m.get("name"))
        concept = concept_of.get(name, "")
        cls = facts.onto.classes.get(concept) if facts.onto is not None and concept else None
        rows.append([f"`{name}`", concept or "—", str(getattr(cls, "identity", "") or m.get("primaryKey") or "—"),
                     getattr(cls, "description", "") or (m.get("properties") or {}).get("pf.description", "") or ""])
    used_roles = sorted({str((c.get("properties") or {}).get("pf.role") or "")
                         for m in manifest.get("models") or [] for c in m.get("columns") or []} - {""})
    lines = ["# Concepts", "", "What each model is an instance of, and how a row is identified.", "",
             *_table(["model", "concept", "identity", "meaning"], rows)]
    if used_roles:
        lines += ["", "## Column roles", "",
                  "Every column carries `pf.role` in the manifest. What a role means for a query:", "",
                  *_table(["role", "rule"], [[f"`{r}`", ROLE_NOTES.get(r, "as named")] for r in used_roles])]
    out["10-concepts.md"] = "\n".join(lines) + "\n"

    # -- metrics and cubes ------------------------------------------------------
    lines = ["# Metrics", ""]
    for cube in cubes:
        lines += [f"## Cube `{cube.get('name')}` on `{cube.get('baseObject')}`", "",
                  "Ask it with `wren cube query --cube <name> --measures <m> --dimensions <d>`; the",
                  "engine writes the GROUP BY.", "", "Measures:", "",
                  *_table(["measure", "expression", "meaning"],
                          [[f"`{x.get('name')}`", f"`{x.get('expression')}`", x.get("description", "")]
                           for x in cube.get("measures") or []]),
                  "",
                  "Dimensions: " + (", ".join(f"`{d.get('name')}`" for d in cube.get("dimensions") or []) or "—"),
                  "Time dimensions: " + (", ".join(f"`{d.get('name')}`"
                                                   for d in cube.get("timeDimensions") or []) or "—"), ""]
    if facts.metrics:
        graph = facts.graph
        rows = []
        for spec in facts.metrics:
            props = (graph.nodes.get(f"metric:{spec.name}") or {}).get("props") or {} if graph else {}
            how = spec.expression or (f"{spec.numerator} / {spec.denominator}" if spec.numerator else spec.kind)
            rows.append([f"`{spec.name}`", spec.kind, f"`{spec.model}`" if spec.model else "—", f"`{how}`",
                         str(props.get("unit") or ""), spec.filter_sql or "", spec.description or spec.label])
        lines += ["## Metric definitions", "", "The governed definitions, as the semantic layer declares them.", "",
                  *_table(["metric", "type", "model", "how", "unit", "filter", "meaning"], rows)]
    out["20-metrics.md"] = "\n".join(lines).rstrip() + "\n"

    # -- governance: policies and decisions, from the graph -------------------
    if facts.graph is not None:
        by_name = lambda n: str(n.get("name"))  # noqa: E731 — a sort key
        pols = sorted((n for n in facts.graph.nodes.values() if n.get("kind") == "Policy"), key=by_name)
        decs = sorted((n for n in facts.graph.nodes.values() if n.get("kind") == "Decision"), key=by_name)
        if pols or decs:
            lines = ["# Governance", ""]
            if pols:
                rows = [[f"`{p.get('name')}`", str((p.get("props") or {}).get("severity") or ""), p.get("label") or ""]
                        for p in pols]
                lines += ["## Policies", "", *_table(["policy", "severity", "rule"], rows), ""]
            if decs:
                rows = [[str(d.get("name")), str((d.get("props") or {}).get("status") or ""), d.get("label") or ""]
                        for d in decs]
                lines += ["## Decisions", "", *_table(["decision", "status", "what was decided"], rows)]
            out["30-governance.md"] = "\n".join(lines).rstrip() + "\n"

    # -- enumerations -----------------------------------------------------------
    enums = manifest.get("enumDefinitions") or []
    if enums:
        lines = ["# Enumerations", "", "The only values these columns take.", ""]
        for e in enums:
            lines += [f"- `{e.get('name')}`: " + ", ".join(f"`{v.get('value')}`" for v in e.get("values") or [])]
        out["40-enums.md"] = "\n".join(lines) + "\n"
    return out


# ------------------------------------------------------------------ build --
@dataclass
class Build:
    """What the workspace is made of: tracked text by relative path, the
    LLM-facing manifest, and what was removed from it."""

    tracked: dict[str, str] = field(default_factory=dict)
    target: dict[str, Any] = field(default_factory=dict)
    hidden: dict[str, list[str]] = field(default_factory=dict)


def build(root: str | Path, group: str, project: str, project_dir: str | Path | None = None,
          manifest: dict[str, Any] | None = None, hide_roles: tuple[str, ...] | list[str] = ()) -> Build:
    root = Path(root)
    d = Path(project_dir) if project_dir else root / "groups" / group / "projects" / project
    if manifest is None:
        manifest = json.loads((d / "mdl" / "mdl.json").read_text(encoding="utf-8"))
    target, hidden = redact(manifest, hide_roles)
    b = Build(target=target, hidden=hidden)
    b.tracked[PROJECT_FILE] = project_yaml(manifest, group, project)
    # The rules describe what the LLM may see, so they are rendered from the
    # redacted manifest: a withheld column has no measure, no dimension and no
    # role in them either.
    for name, text in rules(root, group, project, target, hidden).items():
        b.tracked[f"{RULES_REL}/{name}"] = text
    return b


def write(project_dir: str | Path, b: Build) -> list[Path]:
    """Write the workspace; return what changed. Generated rules the build no
    longer has are removed, a steward's own are never touched."""
    from pf.kg.card import write_if_changed

    ws = workspace(project_dir)
    changed: list[Path] = []
    before = {p: p.read_text(encoding="utf-8") for p in [ws / rel for rel in b.tracked] if p.is_file()}
    for rel, text in b.tracked.items():
        p = ws / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        write_if_changed(p, text)
        if before.get(p) != text:
            changed.append(p)
    rules_dir = ws / RULES_REL
    wanted = {rel.split("/")[-1] for rel in b.tracked if rel.startswith(RULES_REL + "/")}
    for p in sorted(rules_dir.glob("*.md")) if rules_dir.is_dir() else []:
        if GENERATED.match(p.name) and p.name not in wanted:
            p.unlink()
            changed.append(p)
    t = ws / TARGET_REL
    t.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(b.target, indent=2) + "\n"
    if not t.is_file() or t.read_text(encoding="utf-8") != text:
        t.write_text(text, encoding="utf-8")
        changed.append(t)
    (ws / PAIRS_REL).mkdir(parents=True, exist_ok=True)
    return changed


def refresh(root: str | Path, group: str, project: str, project_dir: str | Path | None = None,
            manifest: dict[str, Any] | None = None,
            hide_roles: tuple[str, ...] | list[str] = ()) -> tuple[list[Path], Build]:
    root = Path(root)
    d = Path(project_dir) if project_dir else root / "groups" / group / "projects" / project
    b = build(root, group, project, d, manifest, hide_roles)
    return write(d, b), b


def hide_roles_for(root: str | Path, group: str, project: str) -> tuple[str, ...]:
    """`tools.yaml: wren: {hide_roles: [...]}`, group-inherited, project-overridable."""
    try:
        from pf.tools.config import resolve

        cfg = resolve(Path(root), group, project).get("wren")
    except Exception:  # noqa: BLE001 — a missing or malformed config is the doctor's to report
        return ()
    settings = getattr(cfg, "config", None) or {}
    roles = settings.get("hide_roles") if isinstance(settings, dict) else None
    return tuple(str(r) for r in roles) if isinstance(roles, list) else ()


# ------------------------------------------------------------------ check --
FRONT = re.compile(r"^---\n(.*?)\n---", re.S)


def pairs(project_dir: str | Path) -> list[dict[str, str]]:
    """The remembered questions, as `wren memory store` wrote them."""
    import yaml

    out = []
    for p in sorted((workspace(project_dir) / PAIRS_REL).glob("*.md")):
        m = FRONT.match(p.read_text(encoding="utf-8"))
        data = yaml.safe_load(m.group(1)) if m else None
        out.append({"path": p.name, "nl": str((data or {}).get("nl") or "") if isinstance(data, dict) else "",
                    "sql": str((data or {}).get("sql") or "") if isinstance(data, dict) else ""})
    return out


def check(root: str | Path, group: str, project: str, project_dir: str | Path | None = None,
          plan: bool = True) -> list[str]:
    """Is the committed workspace what the semantic layer projects? Tracked
    inputs only, so it answers the same on a bare runner. With the engine
    present it also plans one query per model against the LLM-facing manifest."""
    root = Path(root)
    d = Path(project_dir) if project_dir else root / "groups" / group / "projects" / project
    label = f"{group}/{project}"
    if not (d / "mdl" / "mdl.json").is_file():
        return []  # no semantic layer yet: nothing to be stale against
    problems: list[str] = []
    try:
        b = build(root, group, project, d, hide_roles=hide_roles_for(root, group, project))
    except Exception as exc:  # noqa: BLE001 — an unbuildable workspace is the finding
        return [f"{label}: workspace cannot be built — {type(exc).__name__}: {exc}"]
    ws = workspace(d)
    for rel, text in b.tracked.items():
        p = ws / rel
        if not p.is_file():
            problems.append(f"{label}: {WORKSPACE_REL}/{rel} is missing")
        elif p.read_text(encoding="utf-8") != text:
            problems.append(f"{label}: {WORKSPACE_REL}/{rel} is stale")
    wanted = {rel.split("/")[-1] for rel in b.tracked if rel.startswith(RULES_REL + "/")}
    rules_dir = ws / RULES_REL
    for p in sorted(rules_dir.glob("*.md")) if rules_dir.is_dir() else []:
        if GENERATED.match(p.name) and p.name not in wanted:
            problems.append(f"{label}: {WORKSPACE_REL}/{RULES_REL}/{p.name} is no longer generated")
    for pair in pairs(d):
        if not (pair["nl"] and pair["sql"]):
            problems.append(f"{label}: {WORKSPACE_REL}/{PAIRS_REL}/{pair['path']} needs `nl` and `sql` front matter")
    if plan and installed() and b.target.get("models"):
        t = ws / TARGET_REL
        t.parent.mkdir(parents=True, exist_ok=True)
        t.write_text(json.dumps(b.target, indent=2) + "\n", encoding="utf-8")
        conn = ws / "connection.json"
        if not conn.is_file():
            conn.write_text(json.dumps({"datasource": "duckdb"}), encoding="utf-8")
        for m in b.target["models"]:
            proc = run(ws, "dry-plan", "--sql", f'select * from "{m["name"]}" limit 1',
                       "--mdl", str(t), "--connection-file", str(conn))
            if proc.returncode:
                tail = (proc.stderr or proc.stdout or "").strip().splitlines()
                why = (tail[-1] if tail else "dry-plan failed")[:160]
                problems.append(f"{label}: `{m['name']}` does not plan — {why}")
    return problems


# ----------------------------------------------------------------- memory --
def index(project_dir: str | Path) -> subprocess.CompletedProcess:
    ws = workspace(project_dir)
    return run(ws, "memory", "index", "--mdl", str(ws / TARGET_REL), "--path", str(ws / MEMORY_REL), timeout=600)


def recall(project_dir: str | Path, question: str, limit: int = 3) -> list[dict[str, Any]]:
    ws = workspace(project_dir)
    proc = run(ws, "memory", "recall", "-q", question, "-l", str(limit), "-o", "json", "--path", str(ws / MEMORY_REL))
    if proc.returncode:
        return []
    try:
        data = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def store(project_dir: str | Path, nl: str, sql: str, tags: str = "") -> subprocess.CompletedProcess:
    """Remember a question and the SQL that answered it, as a tracked file a
    reviewer can read — the pair reaches other agents through a pull request."""
    ws = workspace(project_dir)
    args = ["memory", "store", "--nl", nl, "--sql", sql, "--path", str(ws / MEMORY_REL)]
    if tags:
        args += ["--tags", tags]
    return run(ws, *args)


def instructions(project_dir: str | Path) -> str:
    """The rules, as Wren hands them to a model."""
    proc = run(workspace(project_dir), "context", "instructions")
    if proc.returncode:
        ws = workspace(project_dir) / RULES_REL
        return "\n\n".join(p.read_text(encoding="utf-8") for p in sorted(ws.glob("*.md"))) if ws.is_dir() else ""
    return proc.stdout


def describe(project_dir: str | Path) -> str:
    """The LLM-facing schema as plain text. No embedding needed."""
    ws = workspace(project_dir)
    proc = run(ws, "memory", "describe", "--mdl", str(ws / TARGET_REL))
    return proc.stdout if proc.returncode == 0 else ""


def context(project_dir: str | Path, question: str, limit: int = 3) -> dict[str, Any]:
    """Everything an agent reads before planning one question: the rules, the
    questions already answered that resemble it, and the schema it may use."""
    return {"rules": instructions(project_dir), "pairs": recall(project_dir, question, limit),
            "schema": describe(project_dir)}
