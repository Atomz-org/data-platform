"""A project's architecture blueprint: one page, TOGAF-ordered, Miro-ready.

    pf blueprint build <group> <project>     write the page from the project's artefacts
    pf blueprint check [--all]               is every committed page current?

**Every project has one.** A project with a knowledge graph gets a page with no
configuration: the narrative diagrams (context, capabilities, tools, deployment,
orchestration, sequences, governance) and the tables are derived from what the
project already declares — its dlt sources, its enabled tools (`tools.yaml`,
group then project), its models, metrics, dashboards and decisions. `pf
bootstrap` builds it, so a newly scaffolded project has one from its first
bootstrap. `docs/blueprint.yaml` is optional and only *overrides*: prose, any
narrative diagram by key, the tables, the page's path, or `enabled: false`.
What is always derived:

  derived     conceptual ER       kg Concepts the project's tables instantiate,
                                  their Relations and Properties
              physical ER         mdl/mdl.json models, keys and relationships
              model lineage       kg `feeds` and `contains` edges
              column lineage      compiled dbt SQL traced with sqlglot, typed
                                  by the warehouse's own information_schema
              data dictionary     mdl/mdl.json columns and their pf.role
              decisions, counts   kg Decision, Metric and Exposure nodes
  defaults    title, prose, narrative diagrams and tables, from the project's
              facts; each overridable in docs/blueprint.yaml

**Current, not merely present.** The page carries a fingerprint of every file
it is built from (`INPUTS`). `check` recomputes that fingerprint from the tree
and compares, so it needs no warehouse and no dbt build — which is what lets
the commit gate (`gate.yaml` `blueprint_required`) and CI judge it anywhere.
A change to a model, a macro, the graph, the MDL, the project's Python or the
spec therefore lands with a rebuilt page or is refused.

The fingerprint covers the inputs, not the page: it tells a stale page from a
current one, and says nothing about a hand edit to the HTML. The next build
discards one, so there is nothing to protect.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

SPEC = "docs/blueprint.yaml"
DEFAULT_OUTPUT = "docs/architecture-blueprint.html"
#: Bump when the page's shape changes, so every committed page reads stale once.
GENERATOR_VERSION = "2"
#: Project-relative globs whose bytes the page is built from.
INPUTS = (
    SPEC,
    "kg/graph.json",
    "mdl/mdl.json",
    "transform/dbt_project.yml",
    "transform/models/**/*.sql",
    "transform/macros/**/*.sql",
    "src/**/*.py",
    "tools.yaml",
)
#: Group-relative inputs: a group's tools.yaml changes every sister's page.
GROUP_INPUTS = ("tools.yaml",)
_STAMP = re.compile(r'<meta name="pf-blueprint-inputs" content="(sha256:[0-9a-f]{64})">')
_ASSET = Path(__file__).parent / "blueprint_assets" / "blueprint.html"
_MERMAID = "https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js"

LAYER_STYLE = {
    "source": "#475569",
    "raw": "#8A6A1C",
    "seed": "#6B6F2A",
    "staging": "#1F6F8B",
    "intermediate": "#2F7D5B",
    "mart": "#243B6B",
    "report": "#3E4A8A",
    "semantic": "#7A3E8E",
    "serve": "#0F766E",
    "util": "#64748B",
    "ctl": "#9F3A38",
}
LAYER_ORDER = ["raw", "seed", "staging", "intermediate", "mart", "report", "util"]
#: Mermaid refuses a diagram past 50,000 characters or 500 edges by default.
#: Past these, model lineage is drawn per layer instead of per model.
MAX_DIAGRAM_CHARS = 45_000
MAX_DIAGRAM_EDGES = 450


# ------------------------------------------------------------- inputs --
def _glob_re(pattern: str) -> re.Pattern[str]:
    out, i = "", 0
    while i < len(pattern):
        c = pattern[i]
        if pattern.startswith("**/", i):
            out, i = out + "(?:.*/)?", i + 3
            continue
        if pattern.startswith("**", i):
            out, i = out + ".*", i + 2
            continue
        out += "[^/]*" if c == "*" else "[^/]" if c == "?" else re.escape(c)
        i += 1
    return re.compile(f"^{out}$")


_INPUT_RES = [_glob_re(p) for p in INPUTS]


def is_input(rel: str) -> bool:
    """Is this project-relative path one the page is built from?"""
    rel = rel.replace("\\", "/")
    return "__pycache__" not in rel and any(r.match(rel) for r in _INPUT_RES)


def spec_path(project_dir: Path) -> Path:
    return project_dir / SPEC


def has_blueprint(project_dir: Path) -> bool:
    """Every project with a knowledge graph, unless its spec says `enabled: false`."""
    if not (project_dir / "kg" / "graph.json").is_file():
        return False
    return load_spec(project_dir).get("enabled", True) is not False


def load_spec(project_dir: Path) -> dict[str, Any]:
    if not spec_path(project_dir).is_file():
        return {}
    data = yaml.safe_load(spec_path(project_dir).read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{SPEC} must be a mapping")
    return data


def output_path(project_dir: Path, spec: dict[str, Any] | None = None) -> Path:
    spec = load_spec(project_dir) if spec is None else spec
    return project_dir / str(spec.get("output") or DEFAULT_OUTPUT)


def input_files(project_dir: Path) -> list[str]:
    found = set()
    for p in project_dir.rglob("*"):
        if p.is_file():
            rel = p.relative_to(project_dir).as_posix()
            if is_input(rel) and not rel.startswith(("transform/target/", "transform/dbt_packages/")):
                found.add(rel)
    return sorted(found)


def fingerprint(project_dir: Path) -> str:
    """sha256 over the generator version and every input's path and bytes."""
    h = hashlib.sha256(f"pf-blueprint/{GENERATOR_VERSION}\n".encode())
    files = [(rel, project_dir / rel) for rel in input_files(project_dir)]
    files += [
        (f"@group/{rel}", project_dir.parents[1] / rel)
        for rel in GROUP_INPUTS
        if (project_dir.parents[1] / rel).is_file()
    ]
    for rel, path in files:
        h.update(rel.encode() + b"\0")
        h.update(path.read_bytes().replace(b"\r\n", b"\n"))
        h.update(b"\0")
    return "sha256:" + h.hexdigest()


def stamped(page: Path) -> str | None:
    if not page.is_file():
        return None
    m = _STAMP.search(page.read_text(encoding="utf-8", errors="replace")[:4096])
    return m.group(1) if m else None


@dataclass
class Check:
    state: str  # none | missing | stale | current
    output: str  # project-relative page path, "" when none
    message: str


def check(project_dir: Path, group: str = "", project: str = "") -> Check:
    if not has_blueprint(project_dir):
        return Check("none", "", "no knowledge graph yet, or the spec says enabled: false")
    page = output_path(project_dir)
    rel = page.relative_to(project_dir).as_posix()
    verb = f"pf blueprint build {group} {project}".strip()
    have = stamped(page)
    if have is None:
        return Check("missing", rel, f"{rel} is missing or unstamped — run `{verb}`")
    if have != fingerprint(project_dir):
        return Check("stale", rel, f"{rel} is stale against its inputs — run `{verb}` and commit it")
    return Check("current", rel, f"{rel} is current")


# ------------------------------------------------------------- lineage --
def _dbt_name(project_dir: Path) -> str:
    cfg = yaml.safe_load((project_dir / "transform" / "dbt_project.yml").read_text(encoding="utf-8")) or {}
    return str(cfg.get("name") or "")


def _manifest(project_dir: Path, package: str) -> tuple[dict[str, Any], list[Path]]:
    target = project_dir / "transform" / "target"
    found = (
        sorted(target.rglob("manifest.json"), key=lambda p: p.stat().st_mtime, reverse=True) if target.is_dir() else []
    )
    for m in found:
        data = json.loads(m.read_text(encoding="utf-8"))
        if any(
            n.get("resource_type") == "model" and n.get("package_name") == package
            for n in data.get("nodes", {}).values()
        ):
            return data, [p.parent for p in found]
    raise FileNotFoundError(f"no dbt manifest for {package} under transform/target — run a dbt build first")


def _compiled(node: dict[str, Any], package: str, target_dirs: list[Path]) -> str:
    sql = node.get("compiled_code") or ""
    if sql.strip():
        return sql
    for d in target_dirs:
        f = d / "compiled" / package / node["original_file_path"]
        if f.is_file() and f.read_text(encoding="utf-8").strip():
            return f.read_text(encoding="utf-8")
    return ""


def _warehouse_schema(project_dir: Path, group: str, project: str) -> dict[str, Any]:
    import duckdb

    from pf.runtime.warehouse import Warehouse

    path = Path(Warehouse.for_project(project_dir, group, project).path)
    if not path.is_file():
        raise FileNotFoundError(f"warehouse {path} not found — run the project's pipeline first")
    con = duckdb.connect(str(path), read_only=True)
    try:
        rows = con.execute(
            "select table_catalog, table_schema, table_name, column_name, data_type "
            "from information_schema.columns order by 1, 2, 3, ordinal_position"
        ).fetchall()
    finally:
        con.close()
    schema: dict[str, Any] = {}
    for db, sc, t, c, ty in rows:
        schema.setdefault(db, {}).setdefault(sc, {}).setdefault(t, {})[c] = ty
    return schema


def column_lineage(project_dir: Path, group: str, project: str) -> dict[str, dict[str, Any]]:
    """model -> column -> {"from": [[parent, column]], "expr": sql} for every model."""
    from sqlglot import exp
    from sqlglot.lineage import lineage

    package = _dbt_name(project_dir)
    manifest, target_dirs = _manifest(project_dir, package)
    schema = _warehouse_schema(project_dir, group, project)
    names: dict[str, str] = {}
    for s in manifest.get("sources", {}).values():
        names[s["relation_name"].replace('"', "").lower()] = f"{s['source_name']}.{s['name']}"
    models = []
    for n in manifest.get("nodes", {}).values():
        rel = (n.get("relation_name") or "").replace('"', "").lower()
        if n.get("resource_type") == "seed" and rel:
            names[rel] = f"seed.{n['name']}"
        if n.get("resource_type") == "model" and n.get("package_name") == package:
            names[rel] = n["name"]
            models.append(n)
    out: dict[str, dict[str, Any]] = {}
    for n in sorted(models, key=lambda x: x["name"]):
        sql = _compiled(n, package, target_dirs)
        db, sc, t = [x.strip('"') for x in n["relation_name"].split(".")]
        cols = list(schema.get(db, {}).get(sc, {}).get(t, {}))
        out[n["name"]] = {}
        for c in cols:
            try:
                node = lineage(c, sql, schema=schema, dialect="duckdb")
            except Exception:  # noqa: BLE001 — an untraceable column is reported as literal
                out[n["name"]][c] = {"from": [], "expr": ""}
                continue
            parents = set()
            for x in node.walk():
                if isinstance(x.expression, exp.Table):
                    tb = x.expression
                    key = f"{tb.catalog}.{tb.db}.{tb.name}".lower()
                    parents.add((names.get(key, key), x.name.split(".")[-1]))
            expr = node.expression.sql(dialect="duckdb") if node.expression is not None else ""
            out[n["name"]][c] = {"from": [list(p) for p in sorted(parents)], "expr": re.sub(r"\s+", " ", expr)[:220]}
    return out


# ------------------------------------------------------------- mermaid --
def _mid(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", s)


def classdefs(keys: list[str]) -> str:
    return "\n".join(f"  classDef {k} fill:{LAYER_STYLE[k]},stroke:{LAYER_STYLE[k]},color:#ffffff" for k in keys)


def _layer(name: str, kg_layers: dict[str, str]) -> str:
    if name.startswith("seed."):
        return "seed"
    if name.startswith("rpt_"):
        return "report"
    lay = kg_layers.get(name, "")
    if lay:
        return {"marts": "mart", "utils": "util"}.get(lay, lay)
    if "." in name:
        return "raw"
    return "util"


def _type_word(t: str | None) -> str:
    t = (t or "VARCHAR").upper().replace("TIMESTAMP WITH TIME ZONE", "TIMESTAMPTZ")
    return re.sub(r"[^A-Z0-9_]", "_", re.sub(r"\(.*?\)", "", t)).strip("_") or "VARCHAR"


def conceptual_er(kg: dict[str, Any]) -> str:
    nodes = {n["id"]: n for n in kg["nodes"]}
    used = {e["dst"].split(":", 1)[1] for e in kg["edges"] if e["kind"] == "instantiates"}
    rels = [
        n
        for n in kg["nodes"]
        if n["kind"] == "Relation" and (n["props"].get("domain") in used or n["props"].get("range") in used)
    ]
    concepts = set(used) | {r["props"]["domain"] for r in rels} | {r["props"]["range"] for r in rels}
    card = {"MANY_TO_ONE": "}o--||", "ONE_TO_MANY": "||--o{", "ONE_TO_ONE": "||--||", "MANY_TO_MANY": "}o--o{"}
    out = ["erDiagram"]
    for r in sorted(rels, key=lambda r: r["name"]):
        p = r["props"]
        out.append(
            f"  {_mid(p['domain']).upper()} {card.get(p.get('cardinality'), '}o--||')} "
            f'{_mid(p["range"]).upper()} : "{r["name"]}"'
        )
    props: dict[str, list[dict[str, Any]]] = {}
    for n in kg["nodes"]:
        if n["kind"] == "Property" and n["props"].get("concept") in concepts:
            props.setdefault(n["props"]["concept"], []).append(n)
    for c in sorted(concepts):
        out.append(f"  {_mid(c).upper()} {{")
        for p in props.get(c, [])[:8]:
            pp = p["props"]
            key = " PK" if pp.get("is_identity") else ""
            role = f' "{pp["role"]}"' if pp.get("role") else ""
            out.append(f"    {_type_word(pp.get('mdl_type'))} {p['name']}{key}{role}")
        label = (nodes.get(f"concept:{c}", {}).get("label") or "").replace('"', "'")[:60]
        if not props.get(c):
            out.append(f'    CONCEPT definition "{label}"')
        out.append("  }")
    return "\n".join(out)


def _role(column: dict[str, Any]) -> str:
    return (column.get("properties") or {}).get("pf.role", "")


def physical_er(mdl: dict[str, Any]) -> str:
    rels = mdl.get("relationships", [])
    fks: dict[str, dict[str, str]] = {}
    out = ["erDiagram"]
    for r in rels:
        left, right = r["condition"].split("=")
        lm, lc = left.strip().split(".")
        rm, _ = right.strip().split(".")
        fks.setdefault(lm, {})[lc] = rm
        a, b = r["models"]
        out.append(f'  {a.upper()} }}o--|| {b.upper()} : "{lc}"')
    for mo in mdl.get("models", []):
        name, pk = mo["name"], mo.get("primaryKey")
        cols = [c for c in mo["columns"] if not c.get("relationship")]
        chosen = [c for c in cols if c["name"] == pk or c["name"] in fks.get(name, {})]
        for pick in (
            lambda c: _role(c) in ("event_time", "natural_key"),
            lambda c: _role(c) in ("unit_price", "money_amount", "ratio", "quantity", "measure"),
            lambda c: True,
        ):
            for c in cols:
                if c not in chosen and len(chosen) < 8 and pick(c):
                    chosen.append(c)
        out.append(f"  {name.upper()} {{")
        for c in chosen:
            key = "PK" if c["name"] == pk else ("FK" if c["name"] in fks.get(name, {}) else "")
            note = f' "to {fks[name][c["name"]]}"' if key == "FK" else ""
            out.append(f"    {_type_word(c.get('type'))} {c['name']} {key}{note}".rstrip())
        if len(cols) > len(chosen):
            out.append(f'    MORE more_columns "{len(cols) - len(chosen)} more in the data dictionary"')
        out.append("  }")
    return "\n".join(out)


def model_lineage(kg: dict[str, Any], labels: dict[str, str], counts: dict[str, int], mdl: dict[str, Any]) -> str:
    nodes = {n["id"]: n for n in kg["nodes"]}
    kg_layers = {n["name"]: n.get("layer") or "" for n in kg["nodes"] if n["kind"] == "Model"}
    feeds = [
        (e["src"], e["dst"])
        for e in kg["edges"]
        if e["kind"] == "feeds"
        and nodes.get(e["src"], {}).get("kind") in ("Model", "Table")
        and nodes.get(e["dst"], {}).get("kind") == "Model"
    ]
    contains = [
        (e["src"], e["dst"])
        for e in kg["edges"]
        if e["kind"] == "contains" and nodes.get(e["src"], {}).get("kind") == "Source"
    ]
    name = lambda i: i.split(":", 1)[1]  # noqa: E731
    groups: dict[str, set[str]] = {}
    for s, d in feeds:
        for x in (s, d):
            groups.setdefault(_layer(name(x), kg_layers), set()).add(name(x))
    out = ["flowchart LR", '  subgraph SRC["External sources"]']
    for s in sorted({s for s, _ in contains}):
        out.append(f'    {_mid("s_" + name(s))}["{labels.get(name(s), name(s))}"]:::source')
    out.append("  end")
    titles = {
        "raw": "Raw · landed",
        "staging": "Staging",
        "intermediate": "Intermediate",
        "mart": "Marts",
        "report": "Report boards",
        "util": "Utilities",
    }
    for g in ["raw", "staging", "intermediate", "mart", "report", "util"]:
        if groups.get(g):
            out.append(f'  subgraph L_{g}["{titles[g]}"]')
            out += [f'    {_mid(n)}["{n}"]:::{g}' for n in sorted(groups[g])]
            out.append("  end")
    out += [f"  {_mid('s_' + name(s))} --> {_mid(name(d))}" for s, d in sorted(contains)]
    out += [f"  {_mid(name(s))} --> {_mid(name(d))}" for s, d in sorted(feeds)]
    out += [
        '  subgraph SEM["Semantic and serving"]',
        f'    mf["MetricFlow<br/>{counts["metrics"]} metrics"]:::semantic',
        (
            f'    cubes["Wren MDL<br/>{len(mdl.get("models", []))} models · '
            f'{len(mdl.get("relationships", []))} joins · {len(mdl.get("cubes", []))} cubes"]:::semantic'
        ),
        f'    ev["Evidence site<br/>{counts["exposures"]} dashboard exposures"]:::serve',
        '    ask["Ask the data"]:::serve',
        '    om["OpenMetadata catalogue"]:::serve',
        "  end",
    ]
    if groups.get("mart"):
        out += ["  L_mart --> mf", "  L_mart --> cubes", "  L_mart -.-> om"]
    out.append(f"  {'L_report' if groups.get('report') else 'L_mart'} --> ev")
    out += ["  mf --> ev", "  cubes --> ask"]
    out.append(classdefs(["source", "raw", "staging", "intermediate", "mart", "report", "semantic", "serve", "util"]))
    src = "\n".join(out)
    if len(src) <= MAX_DIAGRAM_CHARS and len(feeds) + len(contains) <= MAX_DIAGRAM_EDGES:
        return src
    # Too big to draw per model: one node per layer, edges weighted by count.
    lay = lambda i: _layer(name(i), kg_layers)  # noqa: E731
    flows: dict[tuple[str, str], int] = {}
    for s_, d_ in feeds:
        if lay(s_) != lay(d_):
            flows[(lay(s_), lay(d_))] = flows.get((lay(s_), lay(d_)), 0) + 1
    agg = ["flowchart LR", '  subgraph SRC["External sources"]']
    agg += [
        f'    {_mid("s_" + name(x))}["{labels.get(name(x), name(x))}"]:::source'
        for x in sorted({x for x, _ in contains})
    ]
    agg.append("  end")
    agg += [f'  L_{g}["{titles[g]}<br/>{len(groups[g])} model(s)"]:::{g}' for g in titles if groups.get(g)]
    agg += (
        [f"  {_mid('s_' + name(x))} --> L_raw" for x in sorted({x for x, _ in contains})] if groups.get("raw") else []
    )
    agg += [f'  L_{a} -->|"{n}"| L_{b}' for (a, b), n in sorted(flows.items())]
    agg += out[out.index('  subgraph SEM["Semantic and serving"]') :]
    return "\n".join(agg)


def _trace(lin: dict[str, Any], m: str, c: str, seen: dict | None = None) -> dict:
    seen = {} if seen is None else seen
    if (m, c) in seen:
        return seen
    x = lin.get(m, {}).get(c)
    seen[(m, c)] = x["from"] if x else []
    for pm, pc in seen[(m, c)]:
        _trace(lin, pm, pc, seen)
    return seen


def column_diagram(
    lin: dict[str, Any], m: str, c: str, kg_layers: dict[str, str], measures: dict[str, list[str]]
) -> tuple[str, int]:
    t = _trace(lin, m, c)
    by_model: dict[str, set[str]] = {}
    for mm, cc in t:
        by_model.setdefault(mm, set()).add(cc)
    out = ["flowchart LR"]
    order = lambda x: (LAYER_ORDER.index(_layer(x, kg_layers)) if _layer(x, kg_layers) in LAYER_ORDER else 9, x)  # noqa: E731
    for mm in sorted(by_model, key=order):
        out.append(f'  subgraph {_mid("g_" + mm)}["{mm}"]')
        out += [f'    {_mid(mm + "__" + cc)}["{cc}"]:::{_layer(mm, kg_layers)}' for cc in sorted(by_model[mm])]
        out.append("  end")
    for (mm, cc), parents in sorted(t.items()):
        out += [f"  {_mid(pm + '__' + pc)} --> {_mid(mm + '__' + cc)}" for pm, pc in parents]
    for mm, cc in sorted(t):
        if mm == m or mm.startswith("fct_"):
            for meas in measures.get(f"{mm}.{cc}", [])[:3]:
                out.append(f'  {_mid("m_" + meas)}(["metric · {meas}"]):::semantic')
                out.append(f"  {_mid(mm + '__' + cc)} -.-> {_mid('m_' + meas)}")
    out.append(classdefs(["raw", "seed", "staging", "intermediate", "mart", "report", "semantic", "util"]))
    return "\n".join(out), len(t)


# ------------------------------------------------------------- defaults --
@dataclass
class Facts:
    """What a project already declares, read for the default narrative."""

    group: str
    project: str
    sources: list[tuple[str, str, list[str]]]  # (name, label, tables)
    tools: list[str]
    reporting: bool
    seeds: bool
    package: str
    warehouse: str
    layers: dict[str, int]
    metrics: int
    exposures: int
    tests: int
    decisions: int
    mdl_models: int
    mdl_rels: int
    cubes: int

    @property
    def wren(self) -> bool:
        return "wren" in self.tools and self.mdl_models > 0

    def has(self, tool: str) -> bool:
        return tool in self.tools


def facts(
    project_dir: Path, group: str, project: str, kg: dict[str, Any], mdl: dict[str, Any], labels: dict[str, str]
) -> Facts:
    root = project_dir.parents[3]
    try:
        from pf.tools.config import enabled_names

        tools = enabled_names(root, group, project)
    except Exception:  # noqa: BLE001 — no tools config reads as no tools
        tools = []
    nodes = {n["id"]: n for n in kg["nodes"]}
    sources = []
    for s in sorted((n for n in kg["nodes"] if n["kind"] == "Source"), key=lambda n: n["name"]):
        tables = sorted(
            nodes[e["dst"]]["name"]
            for e in kg["edges"]
            if e["kind"] == "contains" and e["src"] == s["id"] and e["dst"] in nodes
        )
        sources.append((s["name"], labels.get(s["name"], s["name"]), tables))
    layers: dict[str, int] = {}
    for n in kg["nodes"]:
        if n["kind"] == "Model":
            layers[n.get("layer") or "other"] = layers.get(n.get("layer") or "other", 0) + 1
    src = project_dir / "src"
    package = (
        next((p.name for p in sorted(src.iterdir()) if p.is_dir() and (p / "__init__.py").is_file()), "")
        if src.is_dir()
        else ""
    )
    count = lambda k: sum(n["kind"] == k for n in kg["nodes"])  # noqa: E731
    return Facts(
        group=group,
        project=project,
        sources=sources,
        tools=tools,
        reporting=(project_dir / "reporting").is_dir(),
        seeds=any((project_dir / "transform" / "seeds").rglob("*.csv"))
        if (project_dir / "transform" / "seeds").is_dir()
        else False,
        package=package,
        warehouse=f"data/{project.replace('-', '_')}.duckdb",
        layers=layers,
        metrics=count("Metric"),
        exposures=count("Exposure"),
        tests=count("Test"),
        decisions=count("Decision"),
        mdl_models=len(mdl.get("models", [])),
        mdl_rels=len(mdl.get("relationships", [])),
        cubes=len(mdl.get("cubes", [])),
    )


def _q(s: str) -> str:
    return s.replace('"', "'")


def default_diagrams(f: Facts) -> dict[str, str]:
    """The narrative diagrams, drawn from what the project declares. A tool that
    is not enabled is not drawn: the page describes this project, not the menu."""
    d: dict[str, str] = {}
    loc = f"{f.group}__{f.project}"
    src_nodes = [f'    x_{_mid(n)}["{_q(label)}"]:::source' for n, label, _ in f.sources] or [
        '    x_none["No dlt source yet"]:::source'
    ]

    # ---- A · context
    ctx = [
        "flowchart LR",
        '  subgraph ACT["People"]',
        '    a1["Analysts and report readers"]',
        '    a2["Data and analytics engineers"]',
        '    a3["Governance and risk"]',
        "  end",
        '  subgraph EXT["External data"]',
        *src_nodes,
        "  end",
        f'  subgraph PF["{f.project} on the data platform"]',
        '    p1["Acquire and land<br/>dlt"]:::raw',
        '    p2["Model and test<br/>dbt on DuckDB"]:::mart',
        f'    p3["Measure<br/>MetricFlow{" · Wren MDL" if f.wren else ""}"]:::semantic',
    ]
    serve = [x for x, on in (("Evidence", f.reporting), ("Ask the data", f.wren and f.reporting)) if on]
    if serve:
        ctx.append(f'    p4["Publish<br/>{" · ".join(serve)}"]:::serve')
    cat = [x for x, on in (("OpenMetadata", f.has("openmetadata")), ("OKF", f.has("okf"))) if on]
    if cat:
        ctx.append(f'    p5["Catalogue<br/>{" · ".join(cat)}"]:::serve')
    ctx += [
        '    p6["Orchestrate<br/>Dagster"]:::ctl',
        '    p7["Govern<br/>gate · provenance · AIR"]:::ctl',
        "  end",
        '  subgraph AI["AI services"]',
        '    c2["Claude Code sessions<br/>pf MCP server"]',
    ]
    if f.wren:
        ctx.append('    c1["Claude API<br/>wren_planner agent"]')
    ctx += ["  end", '  gh["GitHub<br/>PRs · Actions"]']
    ctx += [f"  x_{_mid(n)} --> p1" for n, _, _ in f.sources]
    ctx += [
        "  p1 --> p2 --> p3",
        "  p6 -.-> p1",
        "  p6 -.-> p2",
        "  p7 -.-> p2",
        "  a2 --> p2",
        "  a2 --> gh",
        "  a3 --> p7",
        "  gh --> p7",
        "  c2 --> p2",
    ]
    if serve:
        ctx += ["  p3 --> p4", "  p6 -.-> p4", "  a1 --> p4"]
    if cat:
        ctx += ["  p2 --> p5", "  p6 -.-> p5"]
    if f.wren and serve:
        ctx.append("  c1 --> p4")
    d["context"] = "\n".join(ctx) + "\n" + classdefs(["source", "raw", "mart", "semantic", "serve", "ctl"])

    # ---- B · capabilities
    cap = ["flowchart LR", '  subgraph C1["1 Acquire and land"]', "    direction TB"]
    cap += [f'    c1_{_mid(n)}["{_q(label)}<br/>{len(t)} table(s)"]:::raw' for n, label, t in f.sources]
    if f.seeds:
        cap.append('    c1_seeds["Reference seeds"]:::raw')
    if not f.sources and not f.seeds:
        cap.append('    c1_none["No source yet"]:::raw')
    cap += ["  end", '  subgraph C2["2 Conform"]', "    direction TB"]
    for lay, label in (("staging", "Staging"), ("intermediate", "Intermediate"), ("marts", "Marts")):
        if f.layers.get(lay):
            cap.append(f'    c2_{lay}["{label}<br/>{f.layers[lay]} model(s)"]:::mart')
    cap += [
        f'    c2_tests["Data tests<br/>{f.tests}"]:::mart',
        "  end",
        '  subgraph C3["3 Measure"]',
        "    direction TB",
        f'    c3_m["Governed metrics<br/>{f.metrics}"]:::semantic',
    ]
    if f.wren:
        cap.append(f'    c3_c["Wren cubes<br/>{f.cubes}"]:::semantic')
    cap += ["  end", '  subgraph C4["4 Publish and ask"]', "    direction TB"]
    cap.append(
        f'    c4_d["Dashboards<br/>{f.exposures} exposure(s)"]:::serve'
        if f.reporting
        else '    c4_d["No reporting site yet"]:::serve'
    )
    if f.wren and f.reporting:
        cap.append('    c4_a["Conversational analytics"]:::serve')
    cap += [
        "  end",
        '  subgraph C5["5 Decide"]',
        "    direction TB",
        '    c5_k["Knowledge graph and context card"]:::serve',
        f'    c5_d["Decision records<br/>{f.decisions}"]:::serve',
    ]
    if cat:
        cap.append(f'    c5_c["Catalogue<br/>{" · ".join(cat)}"]:::serve')
    cap += [
        "  end",
        '  subgraph C6["Across every stage · Governance and change"]',
        "    direction TB",
        '    c6_g["Commit gate and harness maps"]:::ctl',
        '    c6_p["Provenance ledger"]:::ctl',
        '    c6_a["AI controls · FINOS AIR"]:::ctl',
    ]
    if f.has("recce"):
        cap.append('    c6_r["Data diff review · Recce"]:::ctl')
    cap += [
        "  end",
        "  C1 --> C2 --> C3 --> C4 --> C5",
        "  C6 -.- C1",
        "  C6 -.- C5",
        classdefs(["raw", "mart", "semantic", "serve", "ctl"]),
    ]
    d["capability"] = "\n".join(cap)

    # ---- C · applications
    app = [
        "flowchart LR",
        '  subgraph S["Sources"]',
        *[x.replace("x_", "s_") for x in src_nodes],
        "  end",
        '  subgraph ING["Ingestion · dlt Core"]',
        f'    d1["dlt sources<br/>{f.package + ".sources" if f.package else "src/*/sources"}"]:::raw',
        "  end",
        '  subgraph WH["Warehouse · DuckDB"]',
        f'    w1[("{f.warehouse}")]:::mart',
        "  end",
        '  subgraph TR["Transformation"]',
        f'    t1["dbt project<br/>{sum(f.layers.values())} models · {f.tests} tests"]:::mart',
    ]
    if f.has("recce"):
        app.append('    t2["Recce<br/>PR data diff"]:::ctl')
    app += [
        "  end",
        '  subgraph SEM["Semantic layer"]',
        f'    m1["MetricFlow<br/>{f.metrics} metrics"]:::semantic',
        '    k1["pf kg build<br/>kg/graph.json"]:::semantic',
    ]
    if f.wren:
        app.append(f'    k2["pf semantic mdl<br/>mdl/mdl.json · {f.cubes} cubes"]:::semantic')
    if f.has("okf"):
        app.append('    k3["OKF bundle<br/>okf/"]:::semantic')
    app.append("  end")
    if f.reporting or f.wren:
        app.append('  subgraph SRV["Serving"]')
        if f.reporting:
            app.append('    e1["pf report build<br/>Evidence site"]:::serve')
        if f.wren and f.reporting:
            app += ['    e2["Ask the data page"]:::serve', '    a1["pf tool wren api<br/>127.0.0.1:8766"]:::serve']
        if f.wren:
            app.append('    a2["Wren engine"]:::serve')
        app.append("  end")
    if f.has("openmetadata"):
        app += ['  subgraph CAT["Catalogue"]', '    o1["OpenMetadata"]:::serve', "  end"]
    app += ['  subgraph ORC["Orchestration"]', f'    g1["Dagster code location<br/>{loc}"]:::ctl', "  end"]
    app += [f"  s_{_mid(n)} --> d1" for n, _, _ in f.sources]
    app += ["  d1 --> w1", "  t1 <--> w1", "  t1 --> m1", "  t1 --> k1", "  g1 -.-> d1", "  g1 -.-> t1"]
    if f.has("recce"):
        app.append("  t1 --> t2")
    if f.wren:
        app += ["  k1 --> k2", "  k2 --> a2", '  a2 -->|"read-only SQL"| w1']
    if f.has("okf"):
        app.append("  k1 --> k3")
    if f.reporting:
        app += ["  m1 --> e1", "  w1 --> e1", "  g1 -.-> e1"]
    if f.wren and f.reporting:
        app += ["  e1 --> e2", "  e2 --> a1", "  a1 --> a2"]
    if f.has("openmetadata"):
        app += ["  k1 --> o1", "  g1 -.-> o1"]
    app.append(classdefs(["source", "raw", "mart", "semantic", "serve", "ctl"]))
    d["application"] = "\n".join(app)

    # ---- C · Ask the data, where it runs
    if f.wren and f.reporting:
        d["seq_ask"] = "\n".join(
            [
                "sequenceDiagram",
                "  autonumber",
                "  actor U as Analyst",
                "  participant C as Ask the data page",
                "  participant A as wren api :8766",
                "  participant P as Planner chain",
                "  participant X as Wren engine",
                "  participant W as DuckDB read-only",
                "  participant Lg as Ledger",
                "  U->>C: a question in plain words",
                f"  C->>A: POST /api/p/{f.group}/{f.project}/ask",
                "  A->>P: plan against cubes, labels and formats",
                "  P-->>A: plan (Claude API, else claude CLI, else rules)",
                "  A->>A: repair and validate against catalogue and policy",
                "  A->>X: translate the plan to SQL",
                "  X->>W: EXPLAIN (dry run)",
                "  X->>W: execute",
                "  W-->>X: rows",
                "  A->>Lg: intent, decision, execution",
                "  A-->>C: rows, chart hint, formats",
                "  C-->>U: answer and the SQL used",
                "",
            ]
        )

    # ---- D · technology (the shared stack, the same for every project)
    d["technology"] = "\n".join(
        [
            "flowchart TB",
            '  subgraph DEV["Developer workstation"]',
            '    cc["Claude Code session<br/>pf MCP server · hooks"]',
            '    cli["pf CLI · uv venv"]',
            '    ddev["dagster dev<br/>local SQLite instance"]',
            f'    duck[("{f.warehouse}")]',
            "  end",
            '  subgraph STACK["pf_stack container"]',
            '    ngx["nginx :8080"]',
            '    dw["dagster-webserver :3000<br/>+ dagster-daemon"]',
            f'    cs["code server<br/>{loc}"]',
            *(['    om["OpenMetadata :8585"]'] if f.has("openmetadata") else []),
            *(['    rc["recce server<br/>on demand"]'] if f.has("recce") else []),
            "  end",
            '  subgraph DATA["Stateful containers"]',
            '    pg[("Postgres :5432")]',
            *(['    es[("Elasticsearch")]'] if f.has("openmetadata") else []),
            "  end",
            '  subgraph CLOUD["External services"]',
            '    gh["GitHub · Actions"]',
            '    mkt["Source APIs"]',
            *(['    ant["Anthropic API"]'] if f.wren else []),
            "  end",
            "  ngx --> dw",
            "  dw --> cs",
            "  dw --> pg",
            "  cs --> duck",
            "  cs --> mkt",
            "  ddev --> duck",
            "  cc --> cli",
            "  cli --> duck",
            "  cli --> gh",
            *(["  ngx --> om", "  om --> pg", "  om --> es", "  cs --> om"] if f.has("openmetadata") else []),
            *(["  ngx --> rc"] if f.has("recce") else []),
            *(["  cli --> ant"] if f.wren else []),
            "",
        ]
    )

    # ---- E · orchestration
    orc = ["flowchart LR", f'  subgraph J["Dagster code location {loc} · writer pool limit 1"]']
    orc += [f'    j_{_mid(n)}["dlt · {n}"]:::raw' for n, _, _ in f.sources] or ['    j_none["no dlt asset yet"]:::raw']
    orc.append('    j_dbt["dbt build<br/>models + tests"]:::mart')
    tail = []
    if f.reporting:
        orc.append('    j_ev["Evidence site"]:::serve')
        tail.append("j_ev")
    if f.wren:
        orc.append('    j_wr["wren_semantic_layer"]:::semantic')
        tail.append("j_wr")
    if f.has("okf"):
        orc.append('    j_okf["okf bundle"]:::semantic')
        tail.append("j_okf")
    if f.has("openmetadata"):
        orc.append('    j_om["catalog_sync"]:::serve')
        tail.append("j_om")
    orc.append("  end")
    orc += [f"  j_{_mid(n)} --> j_dbt" for n, _, _ in f.sources]
    orc += [f"  j_dbt --> {t}" for t in tail]
    orc.append(classdefs(["raw", "mart", "semantic", "serve"]))
    d["orchestration"] = "\n".join(orc)

    # ---- G · governance (platform-wide controls, this project's workflow)
    d["governance"] = "\n".join(
        [
            "flowchart LR",
            '  subgraph CH["Change path"]',
            '    c1["Engineer or agent edits"]',
            '    c2["pre-commit gate<br/>file cap · harness maps · blueprint"]:::ctl',
            '    c3["Pull request"]',
            "    c1 --> c2 --> c3",
            "  end",
            '  subgraph CI["GitHub Actions"]',
            '    w1["platform-tests"]:::ctl',
            f'    w2["{f.project}<br/>dbt build · tests"]:::ctl',
            '    w3["ai-governance<br/>provenance · ASQAV · AIR"]:::ctl',
            "  end",
            '  subgraph RT["Runtime controls"]',
            '    r1["Agent action hooks"]:::ctl',
            '    r2["SHA-256 chain + anchor"]:::ctl',
            f'    r3["pf air gate {f.group} {f.project}"]:::ctl',
            "  end",
            "  c3 --> w1",
            "  c3 --> w2",
            "  c3 --> w3",
            "  r1 --> r2 --> w3",
            "  r3 --> w3",
            '  w1 --> merge["Merge to main"]',
            "  w2 --> merge",
            "  w3 --> merge",
            classdefs(["ctl"]),
        ]
    )
    return d


def default_tables(f: Facts) -> dict[str, list[list[str]]]:
    principles = [
        [
            "Business logic does not cross entities",
            "Own warehouse, dlt, dbt and graph; only a rollup reads sisters, read-only.",
            "CLAUDE.md, gate",
        ],
        [
            "dlt lands raw, dbt owns meaning",
            "No transformation in a dlt resource; staging never joins.",
            "group CLAUDE.md",
        ],
        [
            "Joins come from the ontology",
            "MDL join conditions are derived from realises edges, not guessed.",
            "pf semantic mdl",
        ],
        [
            "Generated files come from generators",
            "Docs, indexes, MDL, pages and this blueprint are regenerated, never hand-edited.",
            "pre-commit gate",
        ],
        [
            "Agent actions are recorded",
            "Intent, decision and execution are chained and anchored.",
            "pf provenance verify",
        ],
        [
            "Controls are named, not asserted",
            "Each control carries a FINOS AIR id; coverage is derived.",
            "pf air gate",
        ],
    ]
    blocks = [
        ["Data acquisition", "dlt Core", f"src/{f.package or '*'}/sources", f"{len(f.sources)} source(s)"],
        ["Warehouse", "DuckDB", f.warehouse, "One file per project"],
        ["Transformation", "dbt Core + dbt-duckdb", "transform/", f"{sum(f.layers.values())} models, {f.tests} tests"],
        ["Metrics", "MetricFlow", "transform/models", f"{f.metrics} metrics"],
        ["Knowledge graph", "pf kg", "kg/graph.json", "Models, columns, metrics, concepts, decisions"],
        ["Orchestration", "Dagster", f"code location {f.group}__{f.project}", "Assets, jobs, schedules"],
    ]
    if f.wren:
        blocks.append(
            [
                "Semantic projection",
                "pf semantic mdl + WrenAI",
                "mdl/mdl.json",
                f"{f.mdl_models} models, {f.cubes} cubes",
            ]
        )
    if f.reporting:
        blocks.append(["BI", "Evidence", "reporting/", f"{f.exposures} dashboard exposure(s)"])
    for tool, product, where in (
        ("openmetadata", "OpenMetadata", "catalog/"),
        ("recce", "Recce", "transform/recce.yml"),
        ("okf", "OKF", "okf/"),
    ):
        if f.has(tool):
            blocks.append(
                [tool.capitalize() if tool != "okf" else "Knowledge bundle", product, where, "enabled in tools.yaml"]
            )
    interfaces = [
        [f"I-{i + 1:02d}", label.replace("<br/>", " "), "dlt", "HTTPS", "Dagster asset"]
        for i, (_, label, _) in enumerate(f.sources)
    ]
    more = [
        ["dlt", "DuckDB raw datasets", "dlt destination", "per load"],
        ["dbt", "DuckDB", "SQL", "Dagster dbt assets"],
        ["dbt manifest", "pf kg build", "manifest + YAML meta", "bootstrap, catalog"],
    ]
    if f.wren:
        more += [
            ["kg/graph.json", "pf semantic mdl", "JSON projection", "bootstrap"],
            ["wren api", "DuckDB", "read-only SQL after EXPLAIN", "per question"],
        ]
    if f.has("openmetadata"):
        more.append(["catalog_sync", "OpenMetadata", "REST", "after a run"])
    interfaces += [[f"I-{len(interfaces) + i + 1:02d}", *r] for i, r in enumerate(more)]
    return {"principles": principles, "building_blocks": blocks, "interfaces": interfaces}


def default_text(f: Facts) -> dict[str, str]:
    srcs = ", ".join(label.replace("<br/>", " ") for _, label, _ in f.sources) or "no source yet"
    return {
        "title": f"{f.project} Architecture Blueprint",
        "lede": (
            f"End-to-end architecture of {f.project}: data from {html.escape(srcs)} lands through dlt, "
            "is modelled by dbt "
            f"in DuckDB and measured by MetricFlow{', served to Wren' if f.wren else ''}"
            f"{', published by Evidence' if f.reporting else ''} and orchestrated by Dagster. "
            "Every diagram is generated from the project's own artefacts and configuration; "
            "<code>docs/blueprint.yaml</code> may override any of it."
        ),
    }


def _previous_lineage(page: Path) -> dict[str, Any]:
    """The lineage the committed page already carries, as {model: {col: {from, expr}}}."""
    if not page.is_file():
        return {}
    m = re.search(
        r'<script id="payload" type="application/json">(.*?)</script>', page.read_text(encoding="utf-8"), re.S
    )
    if not m:
        return {}
    try:
        data = json.loads(m.group(1).replace("<\\/", "</"))
    except json.JSONDecodeError:
        return {}
    return {
        mm: {c: {"from": v[0], "expr": v[1]} for c, v in (x.get("cols") or {}).items()}
        for mm, x in (data.get("lineage") or {}).items()
    }


# ------------------------------------------------------------- page --
def _tsv(header: list[str], rows: list[list[Any]]) -> str:
    clean = lambda v: str(v).replace("\t", " ").replace("\n", " ")  # noqa: E731
    return "\n".join(["\t".join(header)] + ["\t".join(clean(v) for v in r) for r in rows])


def _rows_html(rows: list[list[Any]], code_cols: tuple[int, ...] = ()) -> str:
    return "\n".join(
        "<tr>"
        + "".join(
            f"<td><code>{html.escape(str(v))}</code></td>" if i in code_cols else f"<td>{html.escape(str(v))}</td>"
            for i, v in enumerate(r)
        )
        + "</tr>"
        for r in rows
    )


def _render_src(src: str) -> str:
    if src.lstrip().startswith("flowchart"):
        return '%%{init: {"flowchart": {"htmlLabels": false, "curve": "basis"}}}%%\n' + src
    return src


def _figure(key: str, tag: str, title: str, caption: str, src: str, wide: bool = False, anchor: str = "") -> str:
    idattr = f' id="{html.escape(anchor)}"' if anchor else ""
    cap = f"<p>{caption}</p>" if caption else ""
    return (
        f'<figure class="dia" data-key="{html.escape(key)}"{idattr}>'
        f'<figcaption><span class="tag">{html.escape(tag)}</span><h4>{title}</h4>{cap}</figcaption>'
        f'<div class="canvas{" wide" if wide else ""}"><pre class="mermaid">{html.escape(_render_src(src))}</pre></div>'
        f'<div class="tools"></div></figure>'
    )


def _table(
    key: str,
    title: str,
    note: str,
    header: list[str],
    rows: list[list[Any]],
    code_cols: tuple[int, ...] = (),
    anchor: str = "",
    filterable: bool = False,
) -> str:
    idattr = f' id="{anchor}"' if anchor else ""
    flt = (
        f'<input type="search" data-filter="{key}" placeholder="Filter rows" aria-label="Filter {html.escape(title)}"> '
        if filterable
        else ""
    )
    return (
        f'<div class="tablebox" data-table="{key}"{idattr}><div class="head"><div><h3>{html.escape(title)}</h3>'
        f'<p>{note}</p></div><div>{flt}<button type="button" data-copy-table="{key}">Copy as table</button> '
        f'<span class="status" role="status"></span></div></div>'
        f'<div class="scroll"><table><thead><tr>{"".join(f"<th>{html.escape(h)}</th>" for h in header)}</tr></thead>'
        f"<tbody>{_rows_html(rows, code_cols)}</tbody></table></div></div>"
    )


def _section(anchor: str, phase: str, title: str, intro: str, body: list[str]) -> str:
    return (
        f'<section class="phase" id="{anchor}"><div class="phase-head"><span class="ph">{html.escape(phase)}</span>'
        f"<h2>{html.escape(title)}</h2>{f'<p>{intro}</p>' if intro else ''}</div>{''.join(body)}</section>"
    )


def render(project_dir: Path, group: str, project: str, lin: dict[str, Any]) -> str:
    """The page, from the spec, the committed artefacts and the traced lineage."""
    spec = load_spec(project_dir)
    kg = json.loads((project_dir / "kg" / "graph.json").read_text(encoding="utf-8"))
    mdl = json.loads((project_dir / "mdl" / "mdl.json").read_text(encoding="utf-8"))
    f = facts(project_dir, group, project, kg, mdl, spec.get("source_labels") or {})
    text: dict[str, str] = {**default_text(f), **(spec.get("text") or {})}
    diagrams: dict[str, str] = {**default_diagrams(f), **(spec.get("diagrams") or {})}
    derived_tables = default_tables(f)
    t = lambda k, d="": str(text.get(k, d))  # noqa: E731
    kg_layers = {n["name"]: n.get("layer") or "" for n in kg["nodes"] if n["kind"] == "Model"}
    counts = {
        "metrics": sum(n["kind"] == "Metric" for n in kg["nodes"]),
        "exposures": sum(n["kind"] == "Exposure" for n in kg["nodes"]),
    }

    measures: dict[str, list[str]] = {}
    for cube in mdl.get("cubes", []):
        for ms in cube.get("measures", []):
            for c in sorted(set(re.findall(r"[a-z_][a-z0-9_]*", ms.get("expression", "")))):
                if c in lin.get(cube["baseObject"], {}):
                    measures.setdefault(f"{cube['baseObject']}.{c}", []).append(ms["name"])

    all_keys: dict[str, str] = {}
    fig = lambda key, *a, **k: (all_keys.__setitem__(key, a[3]), _figure(key, *a, **k))[1]  # noqa: E731
    sections: list[tuple[str, str, str]] = []  # (anchor, nav phase, nav label)

    def narrative(key: str, tag: str, title: str, caption_key: str, wide: bool = False, anchor: str = "") -> list[str]:
        if key not in diagrams:
            return []
        return [fig(key, tag, title, t(caption_key), str(diagrams[key]).rstrip() + "\n", wide=wide, anchor=anchor)]

    body: list[str] = []
    principles = spec.get("principles") or derived_tables["principles"]
    if principles:
        body.append(
            _section(
                "prelim",
                "Preliminary · Architecture principles",
                t("principles_title", "Architecture principles"),
                t("principles_intro"),
                [
                    _table(
                        "principles",
                        "Principles",
                        f"{len(principles)} principles",
                        ["Principle", "Statement", "Enforced by"],
                        principles,
                    )
                ],
            )
        )
        sections.append(("prelim", "P", "Principles"))
    parts = narrative("context", "A · Context", t("context_title", "System context"), "context_caption")
    if parts:
        body.append(
            _section(
                "vision", "Phase A · Architecture vision", t("vision_title", "System context"), t("vision_intro"), parts
            )
        )
        sections.append(("vision", "A", "Vision and context"))
    parts = narrative(
        "capability", "B · Capabilities", t("capability_title", "Capabilities"), "capability_caption", wide=True
    )
    if parts:
        body.append(
            _section(
                "business",
                "Phase B · Business architecture",
                t("business_title", "Capability map"),
                t("business_intro"),
                parts,
            )
        )
        sections.append(("business", "B", "Business capabilities"))

    # Phase C · data: everything here is derived.
    data = [
        fig(
            "conceptual",
            "C · Conceptual",
            "Ontology concepts and relations",
            "Concepts this project's tables instantiate, their relations and properties, "
            "from <code>kg/graph.json</code>.",
            conceptual_er(kg),
            anchor="conceptual",
        ),
        fig(
            "physical",
            "C · Logical / physical",
            "Mart ER model, as served to Wren",
            f"All {len(mdl.get('models', []))} models and {len(mdl.get('relationships', []))} relationships in "
            "<code>mdl/mdl.json</code>. Each entity shows its primary key, foreign keys, event time and key measures; "
            "the full column list is in the data dictionary.",
            physical_er(mdl),
            wide=True,
            anchor="physical",
        ),
        fig(
            "lineage",
            "C · Lineage",
            "Model-level lineage, source to serving",
            "The <code>contains</code> and <code>feeds</code> edges of the knowledge graph, from each external source "
            "to the semantic layer and the serving tools.",
            model_lineage(kg, spec.get("source_labels") or {}, counts, mdl),
            wide=True,
            anchor="lineage",
        ),
    ]
    focus = [f for f in (spec.get("column_focus") or []) if f.get("column") in lin.get(f.get("model"), {})]
    cards = []
    for f in focus:
        src, n = column_diagram(lin, f["model"], f["column"], kg_layers, measures)
        cards.append(
            fig(
                f"col-{f['model']}-{f['column']}",
                "C · Column lineage",
                f"<code>{html.escape(f['model'])}.{html.escape(f['column'])}</code>",
                f"{html.escape(str(f.get('why', '')))} {n} columns on the path.",
                src,
            )
        )
    if cards:
        data.append(
            '<div class="phase-head" id="collineage"><h3>Column lineage for headline measures</h3>'
            "<p>Traced from the compiled SQL of every model with sqlglot, against the warehouse's real column "
            "types. Solid arrows are derivations; dotted arrows lead to the governed metrics that read "
            "the column.</p></div>"
            f'<div class="grid2">{"".join(cards)}</div>'
        )
    ncols = sum(len(v) for v in lin.values())
    nedges = sum(len(x["from"]) for v in lin.values() for x in v.values())
    if not lin:
        data.append(
            '<div class="explorer" id="explorer"><div class="phase-head"><h3>Column lineage</h3><p>Not traced yet. '
            "Lineage is read from the compiled dbt SQL and the warehouse's column types, and this page was built "
            "where neither was available. Run the project's pipeline, then <code>pf blueprint build "
            f"{html.escape(group)} {html.escape(project)}</code>.</p></div></div>"
        )
    else:
        data.append(
            f'<div class="explorer" id="explorer"><div class="phase-head"><h3>Lineage explorer</h3><p>Pick any of the '
            f"{ncols} columns: every upstream hop back to its raw source or seed, the SQL at each step, "
            "and what reads it "
            'downstream. Copy the trace as a Miro diagram or table.</p></div><div class="pick">'
            '<label for="ex-model">Model<select id="ex-model"></select></label>'
            '<label for="ex-col">Column<select id="ex-col"></select></label>'
            '<button class="primary" id="ex-copy-mmd" type="button">Copy for Miro</button>'
            '<button id="ex-copy-tsv" type="button">Copy as table</button>'
            '<span class="status" id="ex-status" role="status"></span></div><div id="ex-expr" class="expr"></div>'
            '<div class="hops" id="ex-up"></div><div id="ex-down"></div></div>'
        )
        data.append(
            '<div class="tablebox" data-table="lineage"><div class="head"><div><h3>Full column lineage</h3>'
            f"<p>{nedges} edges, one row per parent column.</p></div><div>"
            '<button type="button" data-copy-table="lineage">Copy as table'
            '</button> <span class="status" role="status"></span></div></div><details><summary>Show the table</summary>'
            '<div class="scroll" id="lineage-table"></div></details></div>'
        )
    drows = []
    rels = {}
    for r in mdl.get("relationships", []):
        left, right = r["condition"].split("=")
        rels[tuple(left.strip().split("."))] = right.strip()
    for mo in mdl.get("models", []):
        for c in mo["columns"]:
            if c.get("relationship"):
                continue
            p = c.get("properties") or {}
            key = (
                "PK"
                if c["name"] == mo.get("primaryKey")
                else ("FK → " + rels[(mo["name"], c["name"])] if (mo["name"], c["name"]) in rels else "")
            )
            drows.append(
                [
                    mo["name"],
                    c["name"],
                    c.get("type") or "",
                    key,
                    p.get("pf.role", ""),
                    re.sub(r"\s+", " ", p.get("description", ""))[:240],
                ]
            )
    data.append(
        _table(
            "dictionary",
            "Data dictionary: models served to Wren",
            f"{len(drows)} columns with type, key, semantic role and description.",
            ["Model", "Column", "Type", "Key", "Role", "Description"],
            drows,
            anchor="dictionary",
            filterable=True,
        )
    )
    body.append(
        _section(
            "data",
            "Phase C · Data architecture",
            t("data_title", "From ontology to column"),
            t(
                "data_intro",
                "Four levels: business concepts, the physical models and their joins, lineage between "
                "models, and lineage between individual columns.",
            ),
            data,
        )
    )
    sections += [
        ("data", "C", "Data architecture"),
        ("conceptual", "", "Conceptual model"),
        ("physical", "", "Physical ER"),
        ("lineage", "", "Model lineage"),
    ]
    if cards:
        sections.append(("collineage", "", "Column lineage"))
    sections += [("explorer", "", "Lineage explorer"), ("dictionary", "", "Data dictionary")]

    app = narrative(
        "application",
        "C · Applications",
        t("application_title", "Tool landscape, end to end"),
        "application_caption",
        wide=True,
    )
    app += narrative(
        "seq_ask",
        "C · Interaction",
        t("seq_ask_title", "Conversational analytics"),
        "seq_ask_caption",
        anchor="asksequence",
    )
    interfaces = spec.get("interfaces") or derived_tables["interfaces"]
    if interfaces:
        app.append(
            _table(
                "interfaces",
                "Interface catalogue",
                f"{len(interfaces)} interfaces, with protocol and trigger.",
                ["Id", "From", "To", "Protocol", "Trigger"],
                interfaces,
            )
        )
    if app:
        body.append(
            _section(
                "application",
                "Phase C · Application architecture",
                t("app_title", "How the tools connect"),
                t("app_intro"),
                app,
            )
        )
        sections.append(("application", "C", "Application architecture"))
    parts = narrative(
        "technology", "D · Deployment", t("technology_title", "Processes, ports and stores"), "technology_caption"
    )
    if parts:
        body.append(
            _section(
                "technology",
                "Phase D · Technology architecture",
                t("tech_title", "Where it runs"),
                t("tech_intro"),
                parts,
            )
        )
        sections.append(("technology", "D", "Technology architecture"))
    parts = narrative(
        "orchestration",
        "E · Orchestration",
        t("orchestration_title", "Orchestration"),
        "orchestration_caption",
        wide=True,
    ) + narrative("seq_daily", "F · Run", t("seq_daily_title", "A scheduled run"), "seq_daily_caption")
    if parts:
        body.append(
            _section(
                "orchestration",
                "Phases E and F · Orchestration and runs",
                t("orch_title", "Orchestration"),
                t("orch_intro"),
                parts,
            )
        )
        sections.append(("orchestration", "E/F", "Orchestration and runs"))
    parts = narrative(
        "governance",
        "G · Governance",
        t("governance_title", "Change path and runtime controls"),
        "governance_caption",
        wide=True,
    )
    if parts:
        body.append(
            _section(
                "governance", "Phase G · Implementation governance", t("gov_title", "Controls"), t("gov_intro"), parts
            )
        )
        sections.append(("governance", "G", "Governance"))
    repo = []
    blocks = spec.get("building_blocks") or derived_tables["building_blocks"]
    if blocks:
        repo.append(
            _table(
                "blocks",
                "Solution building blocks",
                f"{len(blocks)} building blocks.",
                ["Building block", "Product", "Where", "Notes"],
                blocks,
            )
        )
    decisions = sorted(
        [
            [n["name"], n.get("label") or "", (n.get("props") or {}).get("status", "")]
            for n in kg["nodes"]
            if n["kind"] == "Decision"
        ]
    )
    if decisions:
        repo.append(
            _table(
                "decisions",
                "Architecture decisions",
                "From the knowledge graph's Decision nodes.",
                ["Record", "Decision", "Status"],
                decisions,
            )
        )
    if repo:
        body.append(
            _section("catalogue", "Phase H · Architecture repository", "Building blocks and decisions", "", repo)
        )
        sections.append(("catalogue", "H", "Catalogues and decisions"))

    def nav_item(anchor: str, phase: str, label: str) -> str:
        mark = f'<span class="ph">{phase}</span>' if phase else ""
        cls = "" if phase else ' class="sub"'
        return f'<li{cls}><a href="#{anchor}">{mark}{html.escape(label)}</a></li>'

    nav = "".join(nav_item(a, ph, lab) for a, ph, lab in sections)
    stats = [
        (len(lin), "dbt models traced"),
        (ncols, "columns with lineage"),
        (nedges, "column-to-column edges"),
        (len(drows), "columns in the dictionary"),
        (len(all_keys), "diagrams, each Miro-ready"),
    ]
    # Copy-as-table text is read from the rendered tables in the page, and the
    # lineage table from the lineage payload, so neither is stored twice.
    payload = {
        "diagrams": all_keys,
        "measures": measures,
        "lineage": {
            m: {"layer": _layer(m, kg_layers), "cols": {c: [x["from"], x["expr"]] for c, x in cols.items()}}
            for m, cols in lin.items()
        },
        "layers": dict(LAYER_STYLE),
        "focus": [focus[0]["model"], focus[0]["column"]] if focus else None,
    }
    title = t("title", f"{project} Architecture Blueprint")
    page = _ASSET.read_text(encoding="utf-8")
    fills = {
        "{{stamp}}": fingerprint(project_dir),
        "{{title}}": html.escape(title),
        "{{eyebrow}}": html.escape(t("eyebrow", f"{group} · {project} · TOGAF 10 ADM views")),
        "{{lede}}": t("lede"),
        "{{nav}}": nav,
        "{{stats}}": "".join(f"<div><b>{v}</b><span>{html.escape(k)}</span></div>" for v, k in stats),
        "{{body}}": "".join(body),
        "{{footer}}": t(
            "footer",
            f"Generated by <code>pf blueprint build {group} {project}</code> from "
            f"<code>groups/{group}/projects/{project}</code>. Column lineage is static analysis "
            "of SQL: it shows which columns an output is computed from, not row-level provenance.",
        ),
        "{{mermaid_src}}": _MERMAID,
        "{{payload}}": json.dumps(payload, separators=(",", ":"), sort_keys=True).replace("</", "<\\/"),
    }
    for k, v in fills.items():
        page = page.replace(k, v)
    left = sorted(set(re.findall(r"\{\{[a-z_]+\}\}", page)))
    if left:
        raise ValueError(f"unfilled placeholders in the blueprint template: {left}")
    return page


def build(project_dir: Path, group: str, project: str) -> tuple[Path, str]:
    """Trace the lineage, render the page, write it. Returns the page and where
    its column lineage came from.

    Lineage needs the compiled SQL and the warehouse. Where either is missing —
    a fresh scaffold, a runner, a machine that has not run the pipeline — the
    page keeps the lineage it already carries rather than losing it, and a page
    that never had any is written without it. The stamp is the same either way:
    it fingerprints the inputs, and a later build with a warehouse fills it in.
    """
    if not has_blueprint(project_dir):
        raise FileNotFoundError(f"{group}/{project} has no knowledge graph yet — run `pf kg build {group} {project}`")
    out = output_path(project_dir)
    try:
        lin, origin = column_lineage(project_dir, group, project), "traced from the compiled SQL"
    except (FileNotFoundError, OSError, ImportError) as exc:
        lin = _previous_lineage(out)
        origin = f"kept from the previous page ({exc})" if lin else f"not available ({exc})"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(project_dir, group, project, lin), encoding="utf-8")
    return out, origin
