"""A project's own atlas — its graph, drawn, in its own folder.

`docs/kg-atlas.html` is the platform's atlas: fourteen node kinds, fourteen
edges, the traversals between them. Those facts are identical in all eight
projects, which is exactly why they live once at the root.

What that page cannot show is *this* project: which of the fourteen kinds it
actually has, what its lineage really looks like, which policies were tightened
locally, and where it is thin. That is per project by construction, so it is
generated per project and written beside the graph it describes —
`groups/<g>/projects/<p>/kg/atlas.html`.

## When it regenerates

An atlas is a picture of the graph, and the graph is a build artefact: it tells
you about the last `pf kg build`, not about the warehouse. So a page generated
at the wrong moment is confidently wrong, and *which* moment is a per-project
decision:

    after_dbt_run    the default. Models exist, the manifest is fresh, and the
                       graph rebuilt from it describes what was just built.
    before_dbt_run   the state going in. Useful when a run is expected to break
                       something and the question afterwards is "what did it
                       look like before".

Both, neither, or either — `atlas.yaml` in the project decides, and the two are
independent because they answer different questions. With `keep_previous` on,
the outgoing page is moved aside rather than overwritten, so the pair can be
diffed.

The hook fires from `pf.runtime.dbt_runtime.dbt`, which every dbt invocation in
this platform funnels through — `seed.py`, `pf seed`, the CLI. It fires only for
`run` and `build`: `dbt parse`, `dbt deps` and `dbt ls` change nothing an atlas
would show, and regenerating on each of them would put three identical rewrites
in front of every real one.

## Configuration layers, like everything else here

    platform defaults  → DEFAULTS below
    group              → groups/<g>/atlas.yaml
    project            → groups/<g>/projects/<p>/atlas.yaml

Later wins, key by key. A group that wants every sister to publish an atlas sets
it once; a project that does not want one says so without arguing with its
siblings.
"""

from __future__ import annotations

import html
import shutil
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

#: Phases the hook understands. Named for the dbt command they bracket rather
#: than for "pre"/"post", so a reader of `atlas.yaml` does not have to know what
#: the hook is attached to.
PHASES = ("before_dbt_run", "after_dbt_run")

#: dbt subcommands that change what an atlas would show. `parse`, `deps`, `ls`,
#: `debug` and `docs` do not, and firing on those would mean three identical
#: regenerations before every real one.
RUN_COMMANDS = frozenset({"run", "build"})

CONFIG_NAME = "atlas.yaml"


@dataclass(frozen=True)
class Config:
    """What a project wants from its atlas."""

    enabled: bool = True
    #: Relative to the project directory. Beside the graph, because that is what
    #: it is a picture of.
    output: str = "kg/atlas.html"
    #: When to regenerate. Empty means "only when asked" — `pf atlas` still works.
    phases: tuple[str, ...] = ("after_dbt_run",)
    #: Move the outgoing page to `<output>.prev.html` instead of overwriting it,
    #: so a before/after pair survives the run that separated them.
    keep_previous: bool = False
    title: str = ""
    #: Sections to render, in this order. Trimming is how a project keeps the
    #: page to the part it actually reads.
    sections: tuple[str, ...] = ("census", "pipeline", "lineage", "governance",
                                 "provenance", "gaps")

    def wants(self, phase: str) -> bool:
        return self.enabled and phase in self.phases


DEFAULTS = Config()

SECTIONS = set(DEFAULTS.sections)


class InvalidConfig(ValueError):
    """An `atlas.yaml` that cannot be honoured. Raised where it is read."""


def _load_one(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        doc = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as exc:
        raise InvalidConfig(f"{path}: {exc}") from exc
    if not isinstance(doc, dict):
        raise InvalidConfig(f"{path}: expected a mapping")
    # Accept both a bare mapping and one nested under `atlas:`, because the
    # group file may grow other sections later and a project file usually does
    # not have any.
    return doc.get("atlas", doc) if isinstance(doc.get("atlas", doc), dict) else {}


def load_config(root: str | Path, group: str, project: str) -> Config:
    """Platform defaults, then the group's file, then the project's."""
    root = Path(root)
    cfg = DEFAULTS
    for path in (root / "groups" / group / CONFIG_NAME,
                 root / "groups" / group / "projects" / project / CONFIG_NAME):
        raw = _load_one(path)
        if not raw:
            continue
        known = set(Config.__dataclass_fields__)
        unknown = set(raw) - known
        if unknown:
            raise InvalidConfig(
                f"{path}: unknown key(s) {sorted(unknown)}; "
                f"valid keys are {sorted(known)}")
        if "phases" in raw:
            bad = set(raw["phases"] or []) - set(PHASES)
            if bad:
                raise InvalidConfig(
                    f"{path}: unknown phase(s) {sorted(bad)}; "
                    f"valid phases are {list(PHASES)}")
            raw["phases"] = tuple(raw["phases"] or ())
        if "sections" in raw:
            bad = set(raw["sections"] or []) - SECTIONS
            if bad:
                raise InvalidConfig(
                    f"{path}: unknown section(s) {sorted(bad)}; "
                    f"valid sections are {sorted(SECTIONS)}")
            raw["sections"] = tuple(raw["sections"] or ())
        cfg = replace(cfg, **raw)
    return cfg


# ------------------------------------------------------------------ facts ----
@dataclass
class Facts:
    group: str
    project: str
    pdir: Path
    counts: dict[str, int] = field(default_factory=dict)
    edges: int = 0
    policies: list[tuple[str, str, str]] = field(default_factory=list)
    chain: list[tuple[str, str]] = field(default_factory=list)
    chain_note: str = ""
    sources: list[str] = field(default_factory=list)
    exposures: list[tuple[str, str]] = field(default_factory=list)
    pii: int = 0
    gaps: list[str] = field(default_factory=list)
    built: str = ""

    @property
    def nodes(self) -> int:
        return sum(self.counts.values())


#: Lineage edges. The semantic and governance planes are true and would turn a
#: five-step example into a forty-step one.
_FLOW = ("feeds", "measures")

PLANES = {
    "Source": "phy", "Table": "phy", "Column": "phy", "Model": "phy",
    "Metric": "phy", "Dimension": "phy", "Test": "phy", "Exposure": "phy",
    "Project": "phy",
    "Concept": "sem", "Property": "sem", "Relation": "sem",
    "Policy": "gov", "Evidence": "gov",
}


def gather(root: str | Path, group: str, project: str) -> Facts:
    """Everything the page needs, read only from this project's own graph."""
    pdir = Path(root) / "groups" / group / "projects" / project
    f = Facts(group=group, project=project, pdir=pdir)

    gp = pdir / "kg" / "graph.duckdb"
    if not gp.exists():
        f.gaps.append("no graph yet — run `pf kg build`, and `pf seed` before that")
        return f
    f.built = datetime.fromtimestamp(gp.stat().st_mtime, UTC).strftime("%Y-%m-%d %H:%M UTC")

    try:
        from pf.kg.store import open_graph

        with open_graph(gp, read_only=True) as g:
            f.counts = {k: v for k, v in g.counts().items() if v}
            f.edges = len(g.edges())
            f.policies = sorted(
                (p.name, str(p.props.get("severity", "")), str(p.props.get("scope", "")))
                for p in g.nodes("Policy"))
            f.sources = sorted({str(t.props.get("source") or "") for t in g.nodes("Table")
                                if t.props.get("source")})
            f.exposures = sorted((e.name, str(e.props.get("owner") or "unowned"))
                                 for e in g.nodes("Exposure"))
            f.pii = sum(1 for c in g.nodes("Column") if c.props.get("pii"))
            f.chain, f.chain_note = _chain(g)
    except Exception as exc:  # noqa: BLE001 — a locked graph must not stop the page
        f.gaps.append(f"graph unreadable ({type(exc).__name__})")
        return f

    if not f.counts.get("Model"):
        f.gaps.append("no models — the dbt manifest was never parsed, so every "
                      "blast radius over this graph comes back empty")
    if not f.counts.get("Metric"):
        f.gaps.append("no metrics — every business question falls back to raw SQL")
    if not f.counts.get("Exposure"):
        f.gaps.append("no exposures — impact analysis stops at the mart and never "
                      "reaches a person to notify")
    return f


def _chain(g, limit: int = 6) -> tuple[list[tuple[str, str]], str]:
    """A real path through this project, most consequential end first."""
    target = None
    for kind in ("Exposure", "Metric", "Model", "Table"):
        pool = sorted(g.nodes(kind), key=lambda n: n.name)
        if kind == "Model":
            pool = [m for m in pool if m.layer == "marts"] or pool
        if pool:
            target = pool[0]
            break
    if target is None:
        return [], "the graph holds nothing to trace yet"

    steps = [(target.kind, target.name)]
    seen, cur, more = {target.id}, target, False
    while True:
        parents = sorted((e for e in g.in_edges(cur.id)
                          if e.kind in _FLOW and e.src not in seen), key=lambda e: e.src)
        if not parents:
            break
        if len(steps) >= limit:
            more = True
            break
        nxt = g.node(parents[0].src)
        if nxt is None:
            break
        seen.add(nxt.id)
        steps.append((nxt.kind, nxt.name))
        cur = nxt
    steps.reverse()
    if len(steps) == 1:
        return steps, "nothing upstream — this node has no lineage yet"
    return steps, "…and further upstream" if more else ""


# ----------------------------------------------------------------- render ----
def esc(text: object, limit: int = 46) -> str:
    """Safe inside a double-quoted mermaid label.

    `#` opens an entity reference and `"` closes the label — either turns the
    diagram into a parse error, which renders as a red box while the job that
    produced it exits 0. `<` is worse: htmlLabels is on, so an owner written
    `Finance <fin@x.test>` has the address parsed as a tag and silently dropped.
    """
    t = " ".join(str(text).split())
    if len(t) > limit:
        t = t[: limit - 1] + "…"
    for a, b in (("#", "#35;"), ('"', "#quot;"), ("<", "#lt;"), (">", "#gt;")):
        t = t.replace(a, b)
    return t


#: Pale fill, saturated stroke of the same hue, near-black ink. Mermaid will not
#: recolour an explicit `classDef` and there is no media query inside a diagram,
#: so the plate sits on a light card in both themes and these values are chosen
#: to read on it. They are the platform atlas's plane colours, unchanged: a
#: reader who has seen one of these pages has read all of them.
MM_INIT = ('%%{init: {"theme":"base","themeVariables":{"lineColor":"#78908b",'
           '"edgeLabelBackground":"#ffffff","primaryTextColor":"#0b0b0b",'
           '"fontFamily":"ui-monospace, SFMono-Regular, Menlo, monospace",'
           '"fontSize":"12px"}}}%%')
MM_CLASSDEF = [
    "  classDef phy fill:#d9f4ee,stroke:#0f766e,stroke-width:1.4px,color:#0b0b0b",
    "  classDef sem fill:#e9e1fb,stroke:#5b21b6,stroke-width:1.4px,color:#0b0b0b",
    "  classDef gov fill:#e0e6ed,stroke:#334155,stroke-width:1.4px,color:#0b0b0b",
    ("  classDef none fill:#f2f6f5,stroke:#93a5a1,stroke-width:1.2px,"
     "stroke-dasharray:4 3,color:#0b0b0b"),
]


def _n(f: Facts, kind: str) -> int:
    return f.counts.get(kind, 0)


def _box(nid: str, label: str, n: int, cls: str) -> str:
    """A stage of the pipeline. Grey and stated as empty when it holds nothing.

    Drawn rather than dropped, so the page has the same shape in every project
    and a hole reads as a hole instead of as something the reader has to notice
    is absent.
    """
    return (f'  {nid}["{label}<br/>{n}"]:::{cls}' if n
            else f'  {nid}["{label}<br/>none yet"]:::none')


def plate_pipeline(f: Facts) -> str:
    src = esc(", ".join(f.sources), 34) if f.sources else ""
    lines = [MM_INIT, "flowchart LR",
             '  subgraph ING["ingest"]', "    direction TB",
             _box("SO", "sources" + (f"<br/>{src}" if src else ""), _n(f, "Source"), "phy"),
             _box("TA", "raw tables", _n(f, "Table"), "phy"),
             "  end",
             '  subgraph TR["transform"]', "    direction TB",
             _box("MO", "models", _n(f, "Model"), "phy"),
             _box("TE", "tests", _n(f, "Test"), "phy"),
             "  end",
             '  subgraph SEMx["semantics"]', "    direction TB",
             _box("ME", "metrics", _n(f, "Metric"), "phy"),
             _box("DI", "dimensions", _n(f, "Dimension"), "phy"),
             _box("CO", "concepts", _n(f, "Concept"), "sem"),
             "  end",
             '  subgraph OUT["delivery + governance"]', "    direction TB",
             _box("EX", "exposures", _n(f, "Exposure"), "phy"),
             _box("PO", "policies", _n(f, "Policy"), "gov"),
             "  end",
             "  SO --> TA --> MO --> ME --> EX",
             "  MO --> DI",
             "  MO -.asserted by.-> TE",
             "  TA -.instantiates.-> CO",
             "  CO -.governed by.-> PO",
             ]
    lines += MM_CLASSDEF
    lines += ['  style ING fill:#f4fbf9,stroke:#0f766e,stroke-dasharray:5 4,color:#0b0b0b',
              '  style TR fill:#f4fbf9,stroke:#0f766e,stroke-dasharray:5 4,color:#0b0b0b',
              '  style SEMx fill:#f8f5fe,stroke:#5b21b6,stroke-dasharray:5 4,color:#0b0b0b',
              '  style OUT fill:#f4f6f9,stroke:#334155,stroke-dasharray:5 4,color:#0b0b0b']
    return "\n".join(lines)


def plate_lineage(f: Facts) -> str:
    if not f.chain:
        return ""
    lines = [MM_INIT, "flowchart LR"]
    ids = []
    for i, (kind, name) in enumerate(f.chain):
        nid = f"X{i}"
        ids.append(nid)
        lines.append(f'  {nid}["{esc(kind, 14)}<br/>{esc(name, 34)}"]'
                     f":::{PLANES.get(kind, 'phy')}")
    lines.append("  " + " --> ".join(ids))
    lines += MM_CLASSDEF
    return "\n".join(lines)


def plate_provenance(f: Facts) -> str:
    lines = [MM_INIT, "flowchart LR",
             '  A1["contracts/annotations.yaml"]:::phy',
             '  A2["transform/target/manifest.json"]:::phy',
             '  A3["semantic_manifest.json"]:::phy',
             '  A4["project ontology<br/>concepts + policy"]:::sem',
             '  A5["data warehouse<br/>information_schema"]:::phy',
             '  B["pf kg build"]:::gov',
             f'  G[("kg/graph.duckdb<br/>{f.nodes} nodes · {f.edges} edges")]:::gov',
             '  C1["kg/context_card.md"]:::none',
             '  C2["kg/atlas.html<br/>this page"]:::none',
             '  C3["impact gate"]:::none',
             "  A1 --> B", "  A2 --> B", "  A3 --> B", "  A4 --> B", "  A5 --> B",
             "  B --> G", "  G --> C1", "  G --> C2", "  G --> C3"]
    lines += MM_CLASSDEF
    return "\n".join(lines)


CSS = """
:root{--ground:#f5f8f7;--surface:#fff;--sunk:#eaf1ef;--ink:#0f1a18;--muted:#566a66;
--faint:#7d8f8b;--hair:#d5e2de;--hair-2:#b9ccc7;--accent:#0d7d72;--plate:#fbfdfc;
--plate-ed:#dfe9e6;--phy:#0f766e;--phy-bg:#d9f4ee;--sem:#5b21b6;--sem-bg:#e9e1fb;
--gov:#334155;--gov-bg:#e0e6ed;--warn:#9a3412;--warn-bg:#fdece4}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--ground:#0b1211;
--surface:#131d1b;--sunk:#101917;--ink:#e8f0ee;--muted:#94a8a3;--faint:#7a8d89;
--hair:#22322f;--hair-2:#2f4340;--accent:#48c2b1;--plate:#e9efed;--plate-ed:#c3d0cd;
--warn:#f0a882;--warn-bg:#2a1a12}}
:root[data-theme="dark"]{--ground:#0b1211;--surface:#131d1b;--sunk:#101917;--ink:#e8f0ee;
--muted:#94a8a3;--faint:#7a8d89;--hair:#22322f;--hair-2:#2f4340;--accent:#48c2b1;
--plate:#e9efed;--plate-ed:#c3d0cd;--warn:#f0a882;--warn-bg:#2a1a12}
*{box-sizing:border-box}
body{background:var(--ground);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,
"Segoe UI",Roboto,Arial,sans-serif;font-size:16.5px;line-height:1.62;margin:0;
padding:0 1.25rem 6rem;-webkit-font-smoothing:antialiased}
.wrap{max-width:62rem;margin:0 auto}.prose{max-width:40rem}
h1,h2{font-family:ui-serif,Georgia,"Iowan Old Style",Palatino,serif;font-weight:600;
text-wrap:balance;letter-spacing:-.011em}
h1{font-size:clamp(2.1rem,5.2vw,3.05rem);line-height:1.08;margin:0 0 .8rem}
h2{font-size:clamp(1.42rem,3vw,1.78rem);line-height:1.2;margin:0 0 .55rem}
.eyebrow{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.705rem;
letter-spacing:.13em;text-transform:uppercase;color:var(--faint)}
code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.855em}
p code,li code,td code{background:var(--sunk);border:1px solid var(--hair);
border-radius:3px;padding:.05em .34em;white-space:nowrap}
p{margin:0 0 1.05rem}a{color:var(--accent)}
header.mast{padding:4.4rem 0 2.2rem;border-bottom:2px solid var(--ink)}
.standfirst{font-size:1.12rem;color:var(--muted);max-width:38rem;margin:0 0 1.6rem}
.mast-meta{display:flex;flex-wrap:wrap;gap:.45rem 1.5rem;font-family:ui-monospace,
SFMono-Regular,Menlo,monospace;font-size:.755rem;color:var(--faint)}
section{padding:3.1rem 0 .4rem;border-top:1px solid var(--hair)}
section:first-of-type{border-top:none}
.sec-head{display:flex;flex-direction:column;gap:.5rem;margin-bottom:1.5rem}
.chip{display:inline-flex;align-items:center;font-family:ui-monospace,SFMono-Regular,
Menlo,monospace;font-size:.7rem;letter-spacing:.05em;text-transform:uppercase;
padding:.16rem .5rem;border-radius:2px;color:#0b0b0b;white-space:nowrap}
.chip.phy{background:var(--phy-bg);border:1px solid var(--phy)}
.chip.sem{background:var(--sem-bg);border:1px solid var(--sem)}
.chip.gov{background:var(--gov-bg);border:1px solid var(--gov)}
.legend{display:flex;flex-wrap:wrap;gap:.55rem;margin:0 0 1.4rem}
figure{margin:1.7rem 0 2rem}
.plate{background:var(--plate);border:1px solid var(--plate-ed);border-radius:3px;
padding:1.5rem 1rem;overflow-x:auto}
.plate pre.mermaid{margin:0;display:block;min-width:min-content}
figcaption{font-size:.86rem;color:var(--muted);margin-top:.7rem;max-width:40rem}
figcaption .lead{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.7rem;
letter-spacing:.11em;text-transform:uppercase;color:var(--faint);display:block;
margin-bottom:.25rem}
.tw{overflow-x:auto;margin:1.4rem 0 1.9rem;border:1px solid var(--hair);border-radius:3px;
background:var(--surface)}
table{border-collapse:collapse;width:100%;font-size:.885rem}
th,td{text-align:left;padding:.56rem .85rem;border-bottom:1px solid var(--hair);
vertical-align:top}
thead th{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.685rem;
letter-spacing:.08em;text-transform:uppercase;color:var(--faint);font-weight:500;
background:var(--sunk);border-bottom:1px solid var(--hair-2)}
tbody tr:last-child td{border-bottom:none}
td.num{text-align:right;font-variant-numeric:tabular-nums;font-family:ui-monospace,
SFMono-Regular,Menlo,monospace}
.dim{color:var(--muted)}
.note{border:1px solid var(--hair-2);border-radius:3px;background:var(--surface);
padding:1.05rem 1.2rem;margin:1.6rem 0}
.note.flag{border-color:var(--warn);background:var(--warn-bg)}
.note .eyebrow{display:block;margin-bottom:.4rem}
.note .eyebrow.w{color:var(--warn)}.note p:last-child{margin-bottom:0}
ul.tight{margin:.4rem 0 1.1rem;padding-left:1.15rem}ul.tight li{margin-bottom:.34rem}
footer{margin-top:3.4rem;padding-top:1.4rem;border-top:2px solid var(--ink);
font-size:.86rem;color:var(--muted)}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
"""


def _plate(body: str, lead: str, caption: str) -> str:
    return (f'<figure><div class="plate"><pre class="mermaid">\n{body}\n</pre></div>'
            f'<figcaption><span class="lead">{html.escape(lead)}</span>'
            f'{caption}</figcaption></figure>')


def _census(f: Facts) -> str:
    rows = []
    for kind, n in sorted(f.counts.items(), key=lambda kv: (-kv[1], kv[0])):
        plane = PLANES.get(kind, "phy")
        rows.append(f'<tr><td><code>{html.escape(kind)}</code></td>'
                    f'<td><span class="chip {plane}">{plane}</span></td>'
                    f'<td class="num">{n}</td></tr>')
    rows.append(f'<tr><td><strong>total</strong></td><td></td>'
                f'<td class="num"><strong>{f.nodes}</strong></td></tr>')
    return ('<div class="tw"><table><thead><tr><th>Node kind</th><th>Plane</th>'
            '<th class="num">Count</th></tr></thead><tbody>'
            + "".join(rows) + "</tbody></table></div>")


def _policies(f: Facts) -> str:
    if not f.policies:
        return '<p class="dim">No policy nodes — the governance plane is empty here.</p>'
    rows = "".join(
        f'<tr><td><code>{html.escape(n)}</code></td><td>{html.escape(sev)}</td>'
        f'<td class="dim">{html.escape(scope or "platform")}</td></tr>'
        for n, sev, scope in f.policies)
    return ('<div class="tw"><table><thead><tr><th>Policy</th><th>Severity</th>'
            '<th>Set by</th></tr></thead><tbody>' + rows + "</tbody></table></div>")


def _head(eyebrow: str, heading: str) -> str:
    return (f'<section><div class="sec-head">'
            f'<span class="eyebrow">{html.escape(eyebrow)}</span>'
            f"<h2>{heading}</h2></div>")


def render(f: Facts, cfg: Config) -> str:
    """The page. Sections in the order `cfg.sections` names them.

    Built by appending rather than by concatenating list literals: every section
    is one `add` of one string, so a section can be reordered or dropped without
    a reader having to work out where one list ended and the next began.
    """
    title = cfg.title or f"{f.project} — project atlas"
    out: list[str] = []
    add = out.append

    add(f"<title>{html.escape(title)}</title>")
    add(f"<style>{CSS}</style>")
    add('<div class="wrap">')
    add('<header class="mast">')
    add(f'<div class="eyebrow">project reference · {html.escape(f.group)}</div>')
    add(f"<h1>{html.escape(title)}</h1>")
    add('<p class="standfirst">The platform atlas says what a graph <em>is</em>. '
        "This one says what <em>this</em> project&rsquo;s graph holds — which "
        "kinds it uses, what its lineage actually looks like, and where it is "
        "thin.</p>")
    add(f'<div class="mast-meta"><span>store: kg/graph.duckdb</span>'
        f"<span>nodes: {f.nodes}</span><span>edges: {f.edges}</span>"
        f"<span>built: {html.escape(f.built or 'never')}</span></div>")
    add("</header>")

    for name in cfg.sections:
        if name == "census":
            add(_head("census", "What this project&rsquo;s graph holds"))
            add('<div class="legend"><span class="chip phy">physical</span>'
                '<span class="chip sem">semantic</span>'
                '<span class="chip gov">governance</span></div>')
            add(_census(f))
            add("</section>")

        elif name == "pipeline":
            add(_head("shape", "Ingest to delivery, with this project&rsquo;s counts"))
            add(_plate(plate_pipeline(f), "plate i — the project, as built",
                       "A stage holding nothing is drawn grey and labelled "
                       "<em>none yet</em> rather than dropped, so the page has the "
                       "same shape in every project and a gap reads as a gap."))
            add("</section>")

        elif name == "lineage" and f.chain:
            add(_head("lineage", "A real path through it"))
            add(_plate(plate_lineage(f), "plate ii — actual names, from the graph",
                       "Chosen downstream-first: an exposure is what somebody "
                       "reads, so the chain ending at one is the chain worth "
                       "showing."))
            if f.chain_note:
                add(f'<p class="dim">{html.escape(f.chain_note)}</p>')
            add("</section>")

        elif name == "governance":
            add(_head("governance", "What must hold, and who set it"))
            add(_policies(f))
            prose = ""
            if f.exposures:
                prose += ("<p><strong>Who to notify:</strong> " + ", ".join(
                    f"<code>{html.escape(n)}</code> → {html.escape(o)}"
                    for n, o in f.exposures[:8]) + "</p>")
            if f.pii:
                prose += (f"<p><strong>PII columns:</strong> {f.pii} — declared, "
                          "not inferred. A column with <code>pii: false</code> "
                          "means <em>not declared</em>, not <em>not "
                          "sensitive</em>.</p>")
            add(f'<div class="prose">{prose}</div>')
            add("</section>")

        elif name == "provenance":
            add(_head("provenance", "Where this graph came from"))
            add(_plate(plate_provenance(f), "plate iii — inputs, store, consumers",
                       "Every input is optional and the builder degrades quietly, "
                       "which is why a thin graph is not obviously a broken one."))
            add("</section>")

        elif name == "gaps" and f.gaps:
            add(_head("gaps", "What this graph cannot answer"))
            items = "".join(f"<li>{html.escape(g)}</li>" for g in f.gaps)
            add('<div class="note flag"><span class="eyebrow w">known gaps</span>'
                f'<ul class="tight">{items}</ul></div>')
            add("</section>")

    add(f"<footer>Generated by <code>pf atlas {html.escape(f.group)} "
        f"{html.escape(f.project)}</code>. Never hand-edit — the next dbt run "
        "overwrites it. Regenerated on: "
        f"{', '.join(cfg.phases) or 'request only'}.</footer>")
    add("</div>")
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ write ----
def write(root: str | Path, group: str, project: str,
          cfg: Config | None = None) -> Path | None:
    """Render the atlas into the project's own folder. None when disabled."""
    cfg = cfg or load_config(root, group, project)
    if not cfg.enabled:
        return None
    f = gather(root, group, project)
    target = f.pdir / cfg.output
    target.parent.mkdir(parents=True, exist_ok=True)
    if cfg.keep_previous and target.exists():
        shutil.copy2(target, target.with_suffix(".prev.html"))
    target.write_text(render(f, cfg))
    return target


def run_phase(project_dir: str | Path, phase: str, command: str = "") -> Path | None:
    """The dbt hook. Silent and harmless when this is not a project.

    Takes a *directory* rather than a group and project because that is what the
    dbt runtime has: `dbt()` is handed a path. Deriving the names from it keeps
    the hook from needing a second argument every caller would have to thread
    through.

    Never raises. An atlas is a convenience, and a broken one must not be able
    to fail a dbt build — the run is the thing that matters.
    """
    if phase not in PHASES:
        return None
    if command and command not in RUN_COMMANDS:
        return None
    try:
        d = Path(project_dir).resolve()
        parts = d.parts
        i = len(parts) - 1 - parts[::-1].index("projects")
        group, project = parts[i - 1], parts[i + 1]
        root = Path(*parts[: i - 2])
        cfg = load_config(root, group, project)
        if not cfg.wants(phase):
            return None
        return write(root, group, project, cfg)
    except Exception:  # noqa: BLE001 — see the docstring
        return None


def default_yaml() -> str:
    """The `atlas.yaml` a new project is scaffolded with."""
    return f"""\
# When this project publishes its atlas, and what goes in it.
#
# Merged over `groups/<group>/{CONFIG_NAME}`, which is merged over the platform
# defaults in `pf.atlas.DEFAULTS`. Set only what differs.
#
#   pf atlas <group> <project>     regenerate now
#   pf atlas --all                 every project
version: 1
atlas:
  enabled: true

  # Written inside this project, beside the graph it describes.
  output: {DEFAULTS.output}

  # Regenerated around `dbt run` and `dbt build` — not around `parse`, `deps` or
  # `ls`, which change nothing an atlas would show.
  #
  #   after_dbt_run    the default: models exist and the manifest is fresh
  #   before_dbt_run   the state going in, for a run expected to break something
  phases:
    - after_dbt_run

  # Move the outgoing page to atlas.prev.html instead of overwriting it, so a
  # before/after pair survives the run that separated them.
  keep_previous: false

  # Trim to the part this project actually reads.
  sections: [{", ".join(DEFAULTS.sections)}]
"""
