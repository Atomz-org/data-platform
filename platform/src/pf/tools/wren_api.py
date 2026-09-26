"""Conversational analytics over one project's Wren workspace, as an HTTP API.

The Evidence page `pages/ask.md` (component `components/WrenChat.svelte`, both
written by `pf report build` for a project with a Wren workspace) talks to this.
It never talks to the warehouse, and neither does anything here except through
the gate:

    question ─► planner ─► plan (validated against the catalogue) ─► wren_gate ─► rows
                 api · claude-cli · rules          cube or one SELECT        translate · policy · plan
                                                                             · dry-run · execute · ledger

**The planner only proposes.** It turns a question into a structured plan: a
cube, its measures, dimensions, a time grain and range, filters, an order —
or, for a question no cube expresses, one SELECT over model names. The plan is
checked against the LLM-facing catalogue (a measure the cube does not have is
refused before anything runs), then it takes the same gated road as
`pf tool wren cube` / `query`, and the answer carries the planned SQL and the
ledger run id. Three planners, the first available wins:

* ``api``        — the Anthropic API through `pf.agents.base`, when credentials resolve.
* ``claude-cli`` — the logged-in `claude` CLI in print mode, tools disabled,
  structured output against the plan's JSON schema. For a laptop with a Claude
  login and no API key.
* ``rules``      — deterministic: measure, dimension, value, grain, range and
  top-N words matched against the catalogue. Always available, offline, and
  the fallback when a model's plan does not validate.

**One project per process.** `pf tool wren api <g> <p>` serves exactly one
workspace, binds 127.0.0.1, and allows a browser origin only on localhost —
the tenancy boundary is the same as the workspace's.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from pf.tools import wren_context as wc

DEFAULT_PORT = 8766
MAX_ROWS = 500
OPS = ("eq", "neq", "in", "not_in", "gt", "gte", "lt", "lte", "contains", "starts_with", "is_null", "is_not_null")
GRAINS = ("day", "week", "month", "quarter", "year")
#: Few enough distinct values to offer, filter by name, and chart as series.
MAX_VALUES = 60


def _today() -> date:
    """The local calendar day: "last month" means the reader's month."""
    return datetime.now(UTC).astimezone().date()


# ---------------------------------------------------------------- catalogue --
def _formats(project_dir: Path) -> dict[str, str]:
    """Each metric's format as the reports render it: the `-- format:` stamp
    `pf report build` writes into every compiled metric query. One source, so
    an answer here reads like the dashboard it sits in."""
    from pf.projections.report_audit import _declared_formats

    return _declared_formats(project_dir / "reporting" / "queries" / "metrics")


def _inferred_formats(project_dir: Path) -> dict[str, str]:
    """Where the reports were never compiled (no `-- format:` stamps), the format
    the report projection *would* declare: `pf.projections.evidence.metric_format`
    over each metric's graph node — unit, label symbol, ISO code, count and money
    words. So a rate still reads as a percent in a project with no dashboard."""
    from pf.projections.evidence import metric_format

    graph = project_dir / "kg" / "graph.json"
    if not graph.is_file():
        return {}
    out = {}
    for n in json.loads(graph.read_text(encoding="utf-8")).get("nodes") or []:
        if n.get("kind") == "Metric":
            if re.search(r"_(pct|percent|share|rate)$", n["name"]):
                out[n["name"]] = "pct1"          # the name says what the number is
                continue
            try:
                out[n["name"]] = metric_format(n["name"], n.get("label") or "", n.get("props") or {})
            except Exception:  # noqa: BLE001 — an odd metric keeps the default
                continue
    return out


def _labels(project_dir: Path) -> dict[str, str]:
    graph = project_dir / "kg" / "graph.json"
    if not graph.is_file():
        return {}
    nodes = json.loads(graph.read_text(encoding="utf-8")).get("nodes") or []
    return {n["name"]: n.get("label") or "" for n in nodes if n.get("kind") in ("Metric", "Dimension")}


def _values(project_dir: Path, group: str, project: str, manifest: dict[str, Any],
            full: dict[str, Any]) -> dict[tuple[str, str], list[str]]:
    """Distinct values of each cube's categorical dimensions, where there are
    few: what a question can filter by name ("gold", "Bullion"). Metadata about
    the catalogue, read-only, never a user's question — so not a ledger run."""
    wh = wc._warehouse(project_dir, group, project)  # noqa: SLF001 — same resolution as the check
    if wh is None:
        return {}
    tables = {m["name"]: m.get("tableReference") or {} for m in full.get("models") or []}
    out: dict[tuple[str, str], list[str]] = {}
    try:
        import duckdb

        con = duckdb.connect(str(wh), read_only=True)
    except Exception:  # noqa: BLE001 — a locked or missing warehouse: no values, still a catalogue
        return {}
    try:
        for cube in manifest.get("cubes") or []:
            base = str(cube.get("baseObject"))
            ref = tables.get(base) or {}
            fq = f'"{ref.get("schema") or "main_marts"}"."{ref.get("table") or base}"'
            for d in cube.get("dimensions") or []:
                col = str(d.get("name"))
                try:
                    rows = con.execute(f'select distinct "{col}" from {fq} where "{col}" is not null '
                                       f"order by 1 limit {MAX_VALUES + 1}").fetchall()
                except Exception:  # noqa: BLE001 — a dimension that is an expression, not a column
                    continue
                if 0 < len(rows) <= MAX_VALUES:
                    out[(base, col)] = [str(r[0]) for r in rows]
    finally:
        con.close()
    return out


def _dim_label(name: str, base: str) -> str:
    """`mcx_commodity` on `fct_mcx_commodity_daily` reads "Commodity": a leading
    token the base model's own name carries is the source, not the meaning."""
    parts = name.split("_")
    if len(parts) > 1 and parts[0] in set(base.split("_")) - {"fct", "dim", "rpt", "is"}:
        return _humanise("_".join(parts[1:]))
    return _humanise(name)


def _humanise(name: str) -> str:
    return name.replace("__", " ").replace("_", " ").strip().capitalize()


@dataclass
class Catalogue:
    group: str
    project: str
    cubes: list[dict[str, Any]]
    models: list[dict[str, Any]]
    formats: dict[str, str]
    rules: str
    suggestions: list[str] = field(default_factory=list)
    noise: set[str] = field(default_factory=set)

    @property
    def empty(self) -> bool:
        return not any(c["measures"] for c in self.cubes)

    def cube(self, name: str) -> dict[str, Any] | None:
        return next((c for c in self.cubes if c["name"] == name), None)

    def as_dict(self) -> dict[str, Any]:
        return {"group": self.group, "project": self.project, "cubes": self.cubes,
                "models": [{"name": m["name"], "description": m["description"],
                            "columns": [c["name"] for c in m["columns"]]} for m in self.models],
                "suggestions": self.suggestions, "empty": self.empty}


_CACHE: dict[str, tuple[tuple[float, float], Catalogue]] = {}


def catalogue(project_dir: str | Path, group: str, project: str) -> Catalogue:
    """The LLM-facing workspace, shaped for a person: cubes with labelled,
    formatted measures and valued dimensions, models with their columns, the
    rules. Cached until the manifest or the warehouse changes."""
    from pf.tools import wren as wt

    d = Path(project_dir)
    target = wt._llm_target(d)  # noqa: SLF001 — the manifest every question is planned against
    wh = wc._warehouse(d, group, project)  # noqa: SLF001
    stamp = (target.stat().st_mtime, wh.stat().st_mtime if wh else 0.0)
    key = str(d.resolve())
    if key in _CACHE and _CACHE[key][0] == stamp:
        return _CACHE[key][1]
    manifest = json.loads(target.read_text(encoding="utf-8"))
    full = json.loads((d / "mdl" / "mdl.json").read_text(encoding="utf-8"))
    formats, labels = _formats(d), _labels(d)
    formats = {**_inferred_formats(d), **formats}
    values = _values(d, group, project, manifest, full)
    cubes = []
    for c in manifest.get("cubes") or []:
        base = str(c.get("baseObject"))
        cubes.append({
            "name": c["name"], "base": base,
            "measures": [{"name": m["name"], "label": m.get("description") or labels.get(m["name"]) or
                          _humanise(m["name"]), "format": formats.get(m["name"], "num2")}
                         for m in c.get("measures") or []],
            "dimensions": [{"name": x["name"], "label": x.get("description") or labels.get(x["name"]) or
                            _dim_label(x["name"], base), "values": values.get((base, x["name"]), [])}
                           for x in c.get("dimensions") or []],
            "timeDimensions": [{"name": x["name"], "label": x.get("description") or _humanise(x["name"])}
                               for x in c.get("timeDimensions") or []],
        })
    cubes.sort(key=lambda c: -len(c["measures"]))
    models = [{"name": m["name"], "description": (m.get("properties") or {}).get("description") or "",
               "columns": [{"name": c["name"], "type": c.get("type"),
                            "role": (c.get("properties") or {}).get("pf.role", "")}
                           for c in m.get("columns") or []]}
              for m in manifest.get("models") or []]
    rules_dir = wc.workspace(d) / wc.RULES_REL
    rules = "\n\n".join(p.read_text(encoding="utf-8") for p in sorted(rules_dir.glob("0[05]-*.md")))
    cat = Catalogue(group, project, cubes, models, formats, rules)
    cat.noise = noise_words(cat)
    cat.suggestions = suggestions(cat)
    _CACHE[key] = (stamp, cat)
    return cat


def noise_words(cat: Catalogue) -> set[str]:
    """Tokens that say where a measure comes from, not what it is: a source or
    system prefix most measure names in this workspace share (`mcx_…`,
    `acme_…`). Learned per catalogue, so no project's vocabulary is written
    into the planner — and a word no longer tells one measure from another."""
    measures = [m for c in cat.cubes for m in c["measures"]]
    if len(measures) < 4:
        return set()
    counts: dict[str, int] = {}
    for m in measures:
        for tok in set(m["name"].split("_")):
            counts[tok] = counts.get(tok, 0) + 1
    # A source prefix is shared by most names and is not a word the labels use
    # as a word — absent from them, or only ever an acronym (MCX). "revenue" or
    # "commodity" appear in labels as meaning, so they stay.
    as_word = {w.lower() for m in measures for w in re.findall(r"[A-Za-z]+", m["label"]) if not w.isupper()}
    return {tok for tok, k in counts.items()
            if k / len(measures) >= 0.5 and len(tok) > 1 and tok not in as_word}


def suggestions(cat: Catalogue, n: int = 6) -> list[str]:
    """Questions this workspace can answer, written from its own catalogue — a
    ranking, a trend (for one value where values are known), a breakdown — in
    the words of its labels. Rates and money first; any real measure will do."""
    out: list[str] = []
    for cube in cat.cubes:
        real = [m for m in cube["measures"] if not _is_component(m)] or cube["measures"]
        rated = sorted(real, key=lambda m: not cat.formats.get(m["name"], "").startswith(("pct", "inr", "usd", "eur")))
        if not rated:
            continue
        dims = [x for x in cube["dimensions"] if not x["name"].startswith("is_")]
        valued = sorted((x for x in dims if 1 < len(x["values"]) <= 30),
                        key=lambda x: (not any(v == v.lower() for v in x["values"][:3]), -len(x["values"])))
        m1, m2, m3 = (_phrase(rated[i % len(rated)]["label"]) for i in (0, len(rated) // 2, -1))
        if valued:
            noun = _clean_label(valued[0]["label"]).lower()
            noun = noun[:-1] + "ies" if noun.endswith("y") and noun[-2:-1] not in "aeiou" else \
                noun if noun.endswith("s") else noun + "s"
            out.append(f"Top 5 {noun} by {m1}")
        elif dims:
            out.append(f"{m1.capitalize()} by {_clean_label(dims[0]['label']).lower()}")
        if cube["timeDimensions"]:
            value = valued[0]["values"][0].replace("_", " ") if valued else ""
            out.append(f"Monthly {m2}" + (f" for {value}" if value else "") + " over the last 12 months")
        other = [x for x in dims if not valued or x["name"] != valued[0]["name"]]
        if other:
            out.append(f"{m3.capitalize()} by {_clean_label(other[0]['label']).lower()}")
        if len(out) >= n:
            break
    seen: set[str] = set()
    unique = []
    for s in out:                     # one question per shape: two cubes often phrase the same one
        key = " ".join(sorted(_content(s)))
        if key not in seen:
            seen.add(key)
            unique.append(s)
    return unique[:n]


# -------------------------------------------------------------------- plans --
@dataclass
class Plan:
    kind: str = "cube"                     # cube | sql | clarify
    interpretation: str = ""
    cube: str = ""
    measures: list[str] = field(default_factory=list)
    dimensions: list[str] = field(default_factory=list)
    time_dimension: str = ""               # a cube time dimension, or ""
    granularity: str = ""
    start: str = ""
    end: str = ""
    filters: list[dict[str, Any]] = field(default_factory=list)   # {dimension, op, values}
    order_by: str = ""
    descending: bool = True
    limit: int = 200
    sql: str = ""
    clarify: str = ""
    planner: str = ""

    def as_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Plan:
        known = set(cls().__dict__)
        return cls(**{k: v for k, v in (raw or {}).items() if k in known})


PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": ["cube", "sql", "clarify"]},
        "interpretation": {"type": "string"},
        "cube": {"type": "string"},
        "measures": {"type": "array", "items": {"type": "string"}},
        "dimensions": {"type": "array", "items": {"type": "string"}},
        "time_dimension": {"type": "string"},
        "granularity": {"type": "string", "enum": ["", *GRAINS]},
        "start": {"type": "string"},
        "end": {"type": "string"},
        "filters": {"type": "array", "items": {"type": "object", "properties": {
            "dimension": {"type": "string"}, "op": {"type": "string", "enum": list(OPS)},
            "values": {"type": "array", "items": {"type": "string"}}},
            "required": ["dimension", "op", "values"]}},
        "order_by": {"type": "string"},
        "descending": {"type": "boolean"},
        "limit": {"type": "integer"},
        "sql": {"type": "string"},
        "clarify": {"type": "string"},
    },
    "required": ["kind", "interpretation"],
}


_TIME_CUE = re.compile(
    r"\b(since|until|before|after|between|during|from|in\s+20\d\d|20\d\d|last|past|previous|this|ytd|"
    r"recent|recently|latest|today|yesterday|week|weeks|month|months|quarter|quarters|year|years|daily|weekly|"
    r"monthly|quarterly|yearly|annual|annually|trend|over time|history|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|"
    r"nov|dec|january|february|march|april|june|july|august|september|october|november|december)\b", re.I)
_RANK_CUE = re.compile(r"\b(top|bottom|highest|lowest|best|worst|most|least|rank|largest|smallest|biggest)\b", re.I)


def repair(plan: Plan, question: str, cat: Catalogue) -> Plan:
    """Take out what a model added and the question never asked for — a
    period, a grain, a ranking — and orderings a time series already has.
    Enforced here rather than hoped for in the prompt: an answer that quietly
    covers "the past week" when nobody said so is a wrong answer that looks
    right."""
    if plan.kind != "cube":
        return plan
    cube = cat.cube(plan.cube) or {}
    times = {x["name"] for c in cat.cubes for x in c["timeDimensions"]}
    if not _TIME_CUE.search(question):
        plan.start = plan.end = plan.granularity = ""
        if plan.time_dimension:
            plan.time_dimension = ""
        plan.filters = [f for f in plan.filters if f.get("dimension") not in times]
    if plan.order_by and (plan.order_by in times or plan.order_by.split("__")[0] in times):
        plan.order_by = ""                                  # a series is already in time order
    if plan.order_by and not _RANK_CUE.search(question):
        plan.order_by = ""
    if plan.granularity and not plan.time_dimension and cube.get("timeDimensions"):
        plan.time_dimension = cube["timeDimensions"][0]["name"]
    if (plan.start or plan.granularity) and not plan.time_dimension and cube.get("timeDimensions"):
        plan.time_dimension = cube["timeDimensions"][0]["name"]
    return plan


def validate(plan: Plan, cat: Catalogue) -> str | None:
    """Why this plan cannot run against this catalogue, or None."""
    if plan.kind == "clarify":
        return None
    if plan.kind == "sql":
        return None if plan.sql.strip() else "an SQL plan with no SQL"
    cube = cat.cube(plan.cube)
    if cube is None:
        return f"no cube `{plan.cube}`"
    have = {m["name"] for m in cube["measures"]}
    dims = {x["name"] for x in cube["dimensions"]}
    times = {x["name"] for x in cube["timeDimensions"]}
    if not plan.measures:
        return "no measure"
    if bad := [m for m in plan.measures if m not in have]:
        return f"`{plan.cube}` has no measure {bad}"
    if bad := [x for x in plan.dimensions if x not in dims]:
        return f"`{plan.cube}` has no dimension {bad}"
    if plan.time_dimension and plan.time_dimension not in times:
        return f"`{plan.cube}` has no time dimension `{plan.time_dimension}`"
    if plan.granularity and plan.granularity not in GRAINS:
        return f"granularity must be one of {GRAINS}"
    for f in plan.filters:
        if f.get("dimension") not in dims | times:
            return f"`{plan.cube}` cannot filter on `{f.get('dimension')}`"
        if f.get("op") not in OPS:
            return f"unknown filter operator `{f.get('op')}`"
    if plan.order_by and plan.order_by not in have | dims:
        return f"cannot order by `{plan.order_by}`"
    return None


# --------------------------------------------------------------- planners --
_WORD = re.compile(r"[a-z0-9]+")
_STOP = {"the", "a", "an", "of", "for", "by", "in", "on", "and", "or", "to", "what", "which", "show", "me",
         "is", "was", "are", "were", "how", "much", "many", "over", "per", "each", "with", "their", "its",
         "last", "this", "top", "bottom", "highest", "lowest", "avg", "average", "total", "all",
         "most", "least", "give", "list", "compare", "vs", "versus", "between", "from", "since", "until",
         "daily", "weekly", "monthly", "quarterly", "yearly", "annual", "trend", "time", "months", "days",
         "weeks", "years", "year", "month", "day", "week", "quarter", "only", "now", "instead", "same", "then",
         "please", "i", "we", "our", "do", "does", "did", "has", "have", "had", "about", "across"}
_SYNONYMS = {"volatility": "vol", "vols": "vol", "returns": "return", "prices": "price", "commodities": "commodity",
             "sessions": "session", "contracts": "contract", "lots": "lot", "spreads": "spread",
             "premiums": "premium", "rupee": "inr", "rupees": "inr", "dollar": "usd", "dollars": "usd",
             "segments": "segment", "yields": "yield", "shares": "share", "days": "day"}
_GRAIN_WORDS = {"daily": "day", "day": "day", "weekly": "week", "week": "week", "monthly": "month", "month": "month",
                "quarterly": "quarter", "quarter": "quarter", "yearly": "year", "annual": "year", "annually": "year",
                "year": "year"}


def _tokens(text: str) -> list[str]:
    return [_SYNONYMS.get(t, t) for t in _WORD.findall(text.lower())]


def _content(text: str) -> set[str]:
    return {t for t in _tokens(text) if t not in _STOP and len(t) > 1}


def _score(words: set[str], name: str, label: str, noise: frozenset[str] | set[str] = frozenset()) -> float:
    target = (_content(name) | _content(label)) - set(noise)
    if not target:
        return 0.0
    hit = words & target
    return len(hit) + len(hit) / len(target)       # coverage breaks ties toward the tighter name


def _time_range(q: str, today: date) -> tuple[str, str]:
    m = re.search(r"\b(?:last|past|previous)\s+(\d+)\s+(day|week|month|quarter|year)s?\b", q)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        days = {"day": 1, "week": 7, "month": 31, "quarter": 92, "year": 366}[unit] * n
        return (today - timedelta(days=days)).isoformat(), today.isoformat()
    m = re.search(r"\b(?:last|past|previous)\s+(day|week|month|quarter|year)\b", q)
    if m:
        days = {"day": 1, "week": 7, "month": 31, "quarter": 92, "year": 366}[m.group(1)]
        return (today - timedelta(days=days)).isoformat(), today.isoformat()
    if re.search(r"\b(this year|ytd|year to date)\b", q):
        return date(today.year, 1, 1).isoformat(), today.isoformat()
    m = re.search(r"\bsince\s+(20\d\d)\b", q)
    if m:
        return f"{m.group(1)}-01-01", today.isoformat()
    m = re.search(r"\bin\s+(20\d\d)\b", q)
    if m:
        return f"{m.group(1)}-01-01", f"{m.group(1)}-12-31"
    return "", ""


_FOLLOW_UP = re.compile(r"^\s*(now|and|also|then|instead|only|just|same|what about|how about|but|for|by|"
                        r"make it|show it|split|break)\b|\binstead\b|\bsame\b", re.I)


def _is_component(m: dict[str, Any]) -> bool:
    """A metric that exists to feed another (a ratio's numerator or count)."""
    return "(component)" in m["label"].lower() or m["name"].endswith(("_total", "_days", "_count"))


def _hits(words: set[str], m: dict[str, Any]) -> set[str]:
    return words & (_content(m["name"]) | _content(m["label"]))


def _phrase(label: str) -> str:
    """A measure label as words in a sentence: "Avg MCX Realised Volatility
    (annualised)" → "realised volatility"."""
    text = re.sub(r"\s*\([^)]*\)|\s+—\s+.*$", "", label)
    text = re.sub(r"^(avg|average)\s+", "", text, flags=re.I).strip()
    words = [w for w in text.split() if not (w.isupper() and len(w) <= 4 and w.isalpha())]
    # "RSI(14)" is all acronym: keep it rather than lose the measure's name
    return " ".join(words).lower() if words else (text or label)


def _clean_label(label: str) -> str:
    return re.sub(r"\s*\((component|flagship)\)|\s+—\s+per\s+\w+", "", label).strip()


def plan_rules(question: str, cat: Catalogue, previous: Plan | None = None, today: date | None = None) -> Plan:
    """A plan from words alone. Good at the questions a cube answers — a
    measure, by some dimensions, over a grain and a range, for some values,
    ranked — and honest (`clarify`) when it cannot place a measure. A question
    that opens like a follow-up ("now for…", "…instead") refines the previous
    plan rather than starting over."""
    today = today or _today()
    q = question.lower()
    # Words that name a breakdown ("by volatility regime") describe the dimension,
    # not the measure: they are taken out before measures are scored.
    by_words: set[str] = set()
    for cube_ in cat.cubes:
        for x in cube_["dimensions"]:
            for phrase in {x["label"].lower(), x["name"].replace("_", " ")}:
                if phrase and re.search(rf"\bby\s+(the\s+)?{re.escape(phrase)}\b", q.replace("_", " ")):
                    by_words |= _content(phrase)
    words = _content(q) - by_words - cat.noise
    wants_parts = bool(re.search(r"\b(total|count|number of|days with|sum)\b", q))

    def rank(m: dict[str, Any]) -> float:
        s = _score(words, m["name"], m["label"], cat.noise)
        if _is_component(m) and not wants_parts:
            s -= 0.75                                # a building block, not an answer
        if m["name"].startswith("avg_") and not wants_parts:
            s += 0.1
        return s

    scored = sorted(((rank(m), cube["name"], m) for cube in cat.cubes for m in cube["measures"]),
                    key=lambda x: -x[0])
    best = scored[0] if scored else (0.0, "", {})
    follow_up = previous is not None and previous.kind == "cube" and bool(_FOLLOW_UP.search(q)) and best[0] < 2.0
    if follow_up:
        plan = Plan.from_dict(previous.as_dict())
        plan.planner, plan.order_by, plan.interpretation = "rules", previous.order_by, ""
    elif best[0] < 1.0:
        options = [_clean_label(m["label"]) for c in cat.cubes[:2] for m in c["measures"] if not _is_component(m)]
        return Plan(kind="clarify", planner="rules",
                    interpretation="No measure in this workspace matches the question.",
                    clarify="Which measure do you mean? For example: " + "; ".join(options[:6]) + ".")
    else:
        cube_name, first = best[1], best[2]
        chosen, covered = [first["name"]], _hits(words, first)
        # "X and Y": add a measure from the same cube only for words the first did not explain
        for s, c, m in scored[1:]:
            if c != cube_name or s < 1.0 or len(chosen) >= 3 or m["name"] in chosen:
                continue
            new = _hits(words, m) - covered
            if new and not (_is_component(m) and not wants_parts):
                chosen.append(m["name"])
                covered |= new
        plan = Plan(cube=cube_name, measures=chosen, planner="rules")
    cube = cat.cube(plan.cube) or {}
    label_text = " ".join(m["label"].lower() for m in cube.get("measures", []) if m["name"] in plan.measures)

    # values named ("gold") → one dimension each: the one whose values match the
    # word as written, then the smallest; several values → a filter and a series
    text = re.sub(r"_", " ", q)
    used: set[str] = set()
    dims = sorted(cube.get("dimensions", []),
                  key=lambda x: (not any(v == v.lower() for v in x["values"][:3]), len(x["values"]) or 999))
    for x in dims:
        if x["name"].startswith("is_"):
            flag = x["name"][3:].replace("_", " ")
            if re.search(rf"\b{re.escape(flag)}\b", text):
                plan.filters = [f for f in plan.filters if f["dimension"] != x["name"]]
                plan.filters.append({"dimension": x["name"], "op": "eq", "values": ["true"]})
            continue
        hits = []
        for v in x["values"]:
            token = v.lower().replace("_", " ")
            if token not in used and re.search(rf"(?<![\w]){re.escape(token)}(?![\w])", text):
                hits.append(v)
                used.add(token)
        if hits:
            plan.filters = [f for f in plan.filters if f["dimension"] != x["name"]]
            plan.filters.append({"dimension": x["name"], "op": "in" if len(hits) > 1 else "eq", "values": hits})
            if len(hits) > 1 and x["name"] not in plan.dimensions:
                plan.dimensions.append(x["name"])
    # dimensions named: "by segment", or every word of the dimension's name present
    for x in cube.get("dimensions", []):
        if x["name"] in plan.dimensions or x["name"].startswith("is_"):
            continue
        name_words = _content(x["name"])
        by = re.search(rf"\bby\s+(the\s+)?({re.escape(x['label'].lower())}|{re.escape(x['name'].replace('_', ' '))}"
                       rf"|{'|'.join(re.escape(w) for w in name_words) or '^$'})\b", text)
        if by or (name_words and name_words <= words and not any(
                f["dimension"] == x["name"] for f in plan.filters)):
            plan.dimensions.append(x["name"])

    # grain — unless the word belongs to the measure ("daily return") — and range
    grain = ""
    toks = _WORD.findall(q)
    for i, tok in enumerate(toks):
        if tok not in _GRAIN_WORDS:
            continue
        nxt = toks[i + 1] if i + 1 < len(toks) else ""
        prv = toks[i - 1] if i else ""
        if (f"{tok} {nxt}" in label_text or prv in ("this", "current", "to", "per", "a", "every")
                or re.search(rf"\b(?:last|past|previous)\s+(?:\d+\s+)?{tok}", q)):
            continue                 # "daily return", "this year", "last 3 months" are not a grain
        grain = _GRAIN_WORDS[tok]
        break
    dim_words = {w for x in cube.get("dimensions", []) for w in _WORD.findall(x["name"])}
    cue = re.search(r"\b(trend|over time|history|evolution)\b", q)
    if not grain and cue and cue.group(1) not in dim_words:      # "trend regime" is a dimension
        grain = "month"
    start, end = _time_range(q, today)
    times = cube.get("timeDimensions") or []
    if (grain or start) and times:
        plan.time_dimension = times[0]["name"]
        plan.granularity = grain or plan.granularity      # a range alone filters, it does not group
        plan.start, plan.end = start or plan.start, end or plan.end

    # ranking
    m = re.search(r"\b(top|bottom|highest|lowest|best|worst)\s*(\d+)?\b", q)
    if m:
        plan.order_by = plan.measures[0]
        plan.descending = m.group(1) in ("top", "highest", "best")
        plan.limit = int(m.group(2) or 5)
        if not plan.dimensions:
            candidates = [x for x in dims if 1 < len(x["values"]) <= MAX_VALUES and not x["name"].startswith("is_")]
            if candidates:
                plan.dimensions.append(candidates[0]["name"])
    plan.interpretation = describe(plan, cat)
    return plan


def _llm_prompt(question: str, cat: Catalogue, previous: Plan | None, today: date) -> str:
    compact = [{"cube": c["name"], "base": c["base"],
                "measures": {m["name"]: m["label"] for m in c["measures"]},
                "dimensions": {x["name"]: (x["values"][:25] if x["values"] else x["label"]) for x in c["dimensions"]},
                "time": [t["name"] for t in c["timeDimensions"]]} for c in cat.cubes]
    models = {m["name"]: [c["name"] for c in m["columns"]] for m in cat.models}
    return (
        "You plan one analytics question over a semantic layer. Output only the JSON plan.\n"
        f"Today is {today.isoformat()}.\n\n"
        "Prefer kind=cube: pick ONE cube and only that cube's measures and dimensions. Use a time "
        "dimension with a granularity for trends, start/end (YYYY-MM-DD) for ranges, filters for named "
        "values (op eq/in/…, values as strings, booleans as 'true'), order_by + descending + limit for "
        "top-N. Set granularity ONLY when the question wants the period broken down (a trend, 'by month'); "
        "a total over a period ('this year', 'last 30 days') is start/end with granularity empty. "
        "Use kind=sql only when no cube can express it: one read-only SELECT over the model names below. "
        "Use kind=clarify with a short question when the request is ambiguous. `interpretation` "
        "restates the question in plain words, naming the measure, breakdown, period and filters.\n"
        "Never add a period, filter, grain or ranking the question does not ask for, and never use a measure "
        "labelled (component) unless the question asks for a total or count.\n\n"
        f"# Rules\n{cat.rules[:6000]}\n\n# Cubes\n{json.dumps(compact)}\n\n# Models\n{json.dumps(models)}\n\n"
        + (f"# The previous question's plan (the new question may refine it)\n{json.dumps(previous.as_dict())}\n\n"
           if previous else "")
        + f"# Question\n{question}\n")


def plan_api(question: str, cat: Catalogue, previous: Plan | None, today: date) -> Plan:
    from pydantic import BaseModel

    from pf.agents import base

    class _Filter(BaseModel):
        dimension: str
        op: str
        values: list[str]

    class _Plan(BaseModel):
        kind: str
        interpretation: str
        cube: str = ""
        measures: list[str] = []
        dimensions: list[str] = []
        time_dimension: str = ""
        granularity: str = ""
        start: str = ""
        end: str = ""
        filters: list[_Filter] = []
        order_by: str = ""
        descending: bool = True
        limit: int = 200
        sql: str = ""
        clarify: str = ""

    parsed, _usage = base.call(
        base.AGENTS["wren_planner"],
        system=[{"type": "text", "text": "You output one JSON analytics plan and nothing else."}],
        user=_llm_prompt(question, cat, previous, today), output_format=_Plan,
        group=cat.group, project=cat.project)
    if parsed is None:
        raise RuntimeError("the model returned no plan")
    plan = Plan.from_dict(parsed.model_dump())
    plan.filters = [dict(f) for f in plan.filters]
    plan.planner = "api"
    return plan


def plan_claude_cli(question: str, cat: Catalogue, previous: Plan | None, today: date,
                    model: str | None = None, timeout: int = 90) -> Plan:
    exe = shutil.which("claude")
    if not exe:
        raise RuntimeError("claude CLI not on PATH")
    proc = subprocess.run(
        [exe, "-p", _llm_prompt(question, cat, previous, today), "--output-format", "json",
         "--model", model or os.environ.get("PF_WREN_PLANNER_MODEL", "haiku"), "--tools", "",
         "--json-schema", json.dumps(PLAN_SCHEMA), "--no-session-persistence"],
        capture_output=True, text=True, timeout=timeout, check=False, cwd=str(Path.home()))
    try:
        out = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"claude CLI returned no JSON: {(proc.stderr or proc.stdout)[-300:]}") from exc
    if out.get("is_error") or not isinstance(out.get("structured_output"), dict):
        raise RuntimeError(f"claude CLI did not plan: {str(out.get('result'))[:300]}")
    plan = Plan.from_dict(out["structured_output"])
    plan.planner = "claude-cli"
    return plan


def planners_available() -> list[str]:
    from pf.agents.base import have_credentials

    out = []
    if have_credentials():
        out.append("api")
    if shutil.which("claude") and os.environ.get("PF_WREN_PLANNER") != "rules":
        out.append("claude-cli")
    out.append("rules")
    return out


def plan(question: str, cat: Catalogue, previous: Plan | None = None, prefer: str = "auto",
         today: date | None = None) -> tuple[Plan, list[str]]:
    """The first planner whose plan validates, and what the others said."""
    today = today or _today()
    order = planners_available() if prefer == "auto" else [prefer, "rules"]
    notes: list[str] = []
    for name in dict.fromkeys(order):
        try:
            p = {"api": plan_api, "claude-cli": plan_claude_cli}.get(name)
            candidate = p(question, cat, previous, today) if p else plan_rules(question, cat, previous, today)
        except Exception as exc:  # noqa: BLE001 — a planner that fails hands over to the next
            notes.append(f"{name}: {type(exc).__name__}: {str(exc)[:200]}")
            continue
        if candidate.planner != "rules":
            candidate = repair(candidate, question, cat)
            if candidate.kind == "cube":
                candidate.interpretation = describe(candidate, cat)
        why = validate(candidate, cat)
        if why is None:
            if not candidate.interpretation or candidate.planner == "rules":
                candidate.interpretation = candidate.interpretation or describe(candidate, cat)
            return candidate, notes
        notes.append(f"{name}: plan refused — {why}")
    return Plan(kind="clarify", planner="none", interpretation="No planner produced a plan this workspace can run.",
                clarify="Try naming a measure, e.g. one of the suggestions."), notes


def describe(plan: Plan, cat: Catalogue) -> str:
    """The plan in plain words, so the reader checks the question was understood."""
    if plan.kind != "cube":
        return plan.interpretation
    cube = cat.cube(plan.cube) or {}
    label = {m["name"]: m["label"] for m in cube.get("measures", [])}
    dlabel = {x["name"]: x["label"] for x in cube.get("dimensions", [])}
    parts = [" and ".join(_clean_label(label.get(m, m)) for m in plan.measures)]
    if plan.dimensions:
        parts.append("by " + ", ".join(_clean_label(dlabel.get(x, x)).lower() for x in plan.dimensions))
    if plan.granularity:
        parts.append({"day": "daily", "week": "weekly", "month": "monthly", "quarter": "quarterly",
                      "year": "yearly"}[plan.granularity])
    if plan.start:
        parts.append(f"{plan.start} to {plan.end or 'today'}")
    ops = {"eq": "", "in": "", "neq": "not ", "not_in": "not ", "gt": "> ", "gte": "≥ ", "lt": "< ", "lte": "≤ ",
           "contains": "contains ", "starts_with": "starts with "}
    for f in plan.filters:
        vals = ", ".join(v.replace("_", " ") for v in f["values"])
        name = _clean_label(dlabel.get(f["dimension"], f["dimension"])).lower()
        if vals == "true":
            parts.append(f"{name} only")
        else:
            parts.append(f"{name}: {ops.get(f['op'], f['op'] + ' ')}{vals}")
    if plan.order_by:
        parts.append(f"{'top' if plan.descending else 'bottom'} {plan.limit}")
    return " · ".join(p for p in parts if p)


# ---------------------------------------------------------------- running --
def cube_args(plan: Plan) -> tuple[list[str], str, list[str]]:
    """A plan as `wren cube query` arguments. A grain groups by the time
    dimension (with the range on it); a range without a grain is a filter, so
    "this year" is one total per group, not one row per day."""
    time_dim = ""
    filters = [f"{f['dimension']}:{f['op']}" + (f":{','.join(f['values'])}" if f.get("values") else "")
               for f in plan.filters]
    if plan.time_dimension and plan.granularity:
        time_dim = f"{plan.time_dimension}:{plan.granularity}"
        if plan.start:
            time_dim += f":{plan.start},{plan.end or _today().isoformat()}"
    elif plan.time_dimension and plan.start:
        end = plan.end or _today().isoformat()
        filters += [f"{plan.time_dimension}:gte:{plan.start}", f"{plan.time_dimension}:lte:{end}"]
    return plan.dimensions, time_dim, filters


def run(project_dir: str | Path, group: str, project: str, plan: Plan, cat: Catalogue,
        root: str | Path | None = None) -> dict[str, Any]:
    """The plan on the gated road; the rows shaped for a person."""
    from pf.tools import wren_gate

    d = Path(project_dir)
    limit = max(1, min(int(plan.limit or 200), MAX_ROWS))
    if plan.kind == "sql":
        out = wren_gate.ask(d, group, project, plan.sql, limit=limit, root=root)
    else:
        dims, time_dim, filters = cube_args(plan)
        # Ranked questions fetch the full breakdown and rank here: the cube has
        # no ORDER BY, and a limit before the sort would rank an arbitrary slice.
        fetch = MAX_ROWS if plan.order_by else limit
        out = wren_gate.ask_cube(d, group, project, plan.cube, plan.measures, dims, time_dim, filters,
                                 limit=fetch, root=root)
    rows = out.rows
    if out.ok and plan.order_by:
        key = plan.order_by
        rows = sorted(rows, key=lambda r: (r.get(key) is None, r.get(key) if r.get(key) is not None else 0),
                      reverse=plan.descending)
        if plan.descending:  # keep nulls last either way
            rows = [r for r in rows if r.get(key) is not None] + [r for r in rows if r.get(key) is None]
        rows = rows[:limit]
    elif out.ok and plan.time_dimension and plan.granularity:
        tcol = next((c for c in out.columns if c.startswith(f"{plan.time_dimension}__")), None)
        if tcol:
            rows = sorted(rows, key=lambda r: str(r.get(tcol)))
    columns = [column_meta(c, plan, cat) for c in out.columns]
    return {
        "ok": out.ok, "stage": out.stage, "message": out.message, "run_id": out.run_id,
        "attempt": out.attempt, "planned_sql": out.planned_sql, "sql": out.sql,
        "columns": columns, "rows": json.loads(json.dumps(rows, default=str)),
        "truncated": len(out.rows) >= limit and not plan.order_by, "limit": limit,
        "chart": chart_hint(columns, rows),
    }


def column_meta(name: str, plan: Plan, cat: Catalogue) -> dict[str, Any]:
    cube = cat.cube(plan.cube) or {}
    measures = {m["name"]: m for m in cube.get("measures", [])}
    dims = {x["name"]: x for x in cube.get("dimensions", [])}
    if name in measures:
        return {"name": name, "kind": "measure", "label": measures[name]["label"], "format": measures[name]["format"]}
    base = name.split("__", 1)[0]
    if plan.time_dimension and plan.granularity and base == plan.time_dimension:
        return {"name": name, "kind": "time", "label": _humanise(base), "grain": plan.granularity or "day"}
    if name in dims:
        return {"name": name, "kind": "dimension", "label": dims[name]["label"]}
    return {"name": name, "kind": "measure" if plan.kind == "sql" else "dimension",
            "label": _humanise(name), "format": cat.formats.get(name, "")}


def chart_hint(columns: list[dict[str, Any]], rows: list[dict[str, Any]]) -> str:
    """Form before colour: a trend is a line, a ranking a bar, one value a
    number, and anything wider a table (dataviz: choosing a form)."""
    kinds = [c["kind"] for c in columns]
    if not rows:
        return "none"
    measures, dims = kinds.count("measure"), kinds.count("dimension")
    tcol = next((c["name"] for c in columns if c["kind"] == "time"), None)
    points = len({r.get(tcol) for r in rows}) if tcol else 0
    if tcol and points < 2:          # one period is a ranking or a number, not a line
        kinds = [k for k in kinds if k != "time"]
    if "time" in kinds and measures >= 1 and dims <= 1 and len(rows) >= 2:
        series = len({r.get(next(c["name"] for c in columns if c["kind"] == "dimension"))
                      for r in rows}) if dims else 1
        return "line" if series <= 8 else "table"
    if dims == 0 and "time" not in kinds and len(rows) == 1:
        return "number"
    if dims == 1 and "time" not in kinds and measures >= 1 and len(rows) <= 30:
        return "bar"
    return "table"


def answer(project_dir: str | Path, group: str, project: str, question: str,
           previous: dict[str, Any] | None = None, prefer: str = "auto",
           root: str | Path | None = None) -> dict[str, Any]:
    """One conversational turn: plan, run, shape. Never raises."""
    cat = catalogue(project_dir, group, project)
    prev = Plan.from_dict(previous) if previous else None
    p, notes = plan(question, cat, prev, prefer)
    turn: dict[str, Any] = {"question": question, "plan": p.as_dict(), "planner": p.planner,
                            "interpretation": p.interpretation, "notes": notes}
    if p.kind == "clarify":
        return {**turn, "ok": False, "stage": "clarify", "message": p.clarify or p.interpretation,
                "columns": [], "rows": [], "chart": "none"}
    return {**turn, **run(project_dir, group, project, p, cat, root)}


# -------------------------------------------------------------------- http --
# Request bodies: module level, because FastAPI resolves annotations by name and
# `from __future__ import annotations` turns every one into a string.
from pydantic import BaseModel  # noqa: E402 — kept beside the HTTP layer it serves


class Ask(BaseModel):
    question: str
    previous: dict[str, Any] | None = None
    planner: str = "auto"

class Cube(BaseModel):
    cube: str
    measures: list[str]
    dimensions: list[str] = []
    time_dimension: str = ""
    granularity: str = ""
    start: str = ""
    end: str = ""
    filters: list[dict[str, Any]] = []
    order_by: str = ""
    descending: bool = True
    limit: int = 200

class Sql(BaseModel):
    sql: str
    limit: int = 200

class Remember(BaseModel):
    question: str
    sql: str


@dataclass(frozen=True)
class Served:
    """One project this process answers for."""
    group: str
    project: str
    project_dir: Path

    @property
    def key(self) -> str:
        return f"{self.group}/{self.project}"


def discover(root: str | Path, group: str | None = None, project: str | None = None) -> list[Served]:
    """The projects to serve: one, one group's, or every project with a Wren
    workspace. A project without one has nothing to ask and is not served."""
    out = []
    for d in sorted(Path(root).glob("groups/*/projects/*")):
        g, p = d.parent.parent.name, d.name
        if (group and g != group) or (project and p != project):
            continue
        if (d / "mdl" / "wren" / "wren_project.yml").is_file():
            out.append(Served(g, p, d.resolve()))
    return out


def status(s: Served) -> dict[str, Any]:
    """Can this project answer at all, and if not, what its owner does next."""
    info: dict[str, Any] = {"group": s.group, "project": s.project, "ready": False}
    if not (s.project_dir / "mdl" / "mdl.json").is_file():
        return {**info, "reason": "no semantic layer yet", "fix": f"uv run pf semantic mdl {s.group} {s.project}"}
    try:
        cat = catalogue(s.project_dir, s.group, s.project)
    except Exception as exc:  # noqa: BLE001 — an unreadable workspace is a status, not a crash
        return {**info, "reason": f"workspace unreadable: {type(exc).__name__}: {str(exc)[:160]}",
                "fix": f"uv run pf tool wren workspace {s.group} {s.project}"}
    wh = wc._warehouse(s.project_dir, s.group, s.project)  # noqa: SLF001
    info |= {"cubes": len(cat.cubes), "measures": sum(len(c["measures"]) for c in cat.cubes),
             "models": len(cat.models), "warehouse": wh is not None}
    if cat.empty and not cat.models:
        return {**info, "reason": "the semantic layer has no models or metrics yet",
                "fix": f"uv run pf seed {s.group} {s.project}  # then pf semantic mdl"}
    if wh is None:
        return {**info, "reason": "no warehouse built — questions plan but cannot run",
                "fix": f"uv run pf seed {s.group} {s.project}", "ready": not cat.empty}
    return {**info, "ready": True}


def create_app(served: list[Served] | str | Path, group: str | None = None, project: str | None = None):
    """The HTTP API for one or many projects.

    Every project lives under its own prefix, `/api/p/<group>/<project>/…`, and
    a request is answered only by the project its path names: the catalogue,
    the planner, the gate and the ledger are that project's alone, exactly as
    the workspace boundary draws it. A page therefore cannot, by pointing at
    the wrong port, query another project's data — an unserved path is a 404
    that names what this process does serve. With a single project the same
    routes are also mounted at `/api/…`.
    """
    from fastapi import APIRouter, FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware

    from pf import obs

    if not isinstance(served, list):                       # create_app(project_dir, group, project)
        served = [Served(str(group), str(project), Path(served))]
    by_key = {s.key: s for s in served}
    app = FastAPI(title="Wren — conversational analytics", docs_url="/api/docs", openapi_url="/api/openapi.json")
    app.add_middleware(CORSMiddleware, allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
                       allow_methods=["GET", "POST"], allow_headers=["content-type"])

    @app.get("/api/projects")
    def projects() -> dict[str, Any]:
        return {"projects": [status(s) for s in served], "planners": planners_available()}

    def router(s: Served) -> APIRouter:
        d, g, p = s.project_dir, s.group, s.project
        root = obs.repo_root(d)
        r = APIRouter()

        @r.get("/health")
        def health() -> dict[str, Any]:
            return {"ok": True, **status(s), "engine": wc.installed(), "planners": planners_available()}

        @r.get("/catalog")
        def catalog() -> dict[str, Any]:
            return catalogue(d, g, p).as_dict()

        @r.post("/ask")
        def ask(body: Ask) -> dict[str, Any]:
            if not body.question.strip():
                raise HTTPException(400, "empty question")
            return answer(d, g, p, body.question.strip(), body.previous, body.planner, root)

        @r.post("/cube")
        def cube(body: Cube) -> dict[str, Any]:
            cat = catalogue(d, g, p)
            plan_ = Plan(kind="cube", planner="builder", **body.model_dump())
            if why := validate(plan_, cat):
                raise HTTPException(400, why)
            plan_.interpretation = describe(plan_, cat)
            return {"question": plan_.interpretation, "plan": plan_.as_dict(), "planner": "builder",
                    "interpretation": plan_.interpretation, "notes": [], **run(d, g, p, plan_, cat, root)}

        @r.post("/sql")
        def sql(body: Sql) -> dict[str, Any]:
            cat = catalogue(d, g, p)
            plan_ = Plan(kind="sql", sql=body.sql, limit=body.limit, planner="sql", interpretation="Your SQL")
            return {"question": body.sql, "plan": plan_.as_dict(), "planner": "sql", "interpretation": "Your SQL",
                    "notes": [], **run(d, g, p, plan_, cat, root)}

        @r.post("/remember")
        def remember(body: Remember) -> dict[str, Any]:
            from pf.tools import wren_gate

            if why := wren_gate.policy(body.sql):
                raise HTTPException(400, why)
            proc = wc.store(d, body.question, body.sql)
            if proc.returncode:
                raise HTTPException(500, (proc.stderr or proc.stdout or "store failed")[-400:])
            return {"ok": True, "message": (proc.stdout or "").strip()[-300:]}

        @r.get("/recall")
        def recall(q: str) -> dict[str, Any]:
            return {"pairs": wc.recall(d, q, 3)}

        return r

    for s in served:
        app.include_router(router(s), prefix=f"/api/p/{s.group}/{s.project}")
    if len(served) == 1:
        app.include_router(router(served[0]), prefix="/api")

    @app.api_route("/api/p/{group}/{project}/{rest:path}", methods=["GET", "POST"])
    def unserved(group: str, project: str, rest: str) -> None:
        raise HTTPException(404, {"message": f"{group}/{project} is not served here",
                                  "served": sorted(by_key), "fix": f"uv run pf tool wren api {group} {project}"
                                                                   " (or --all)"})

    return app


def serve(served: list[Served] | str | Path, group: str | None = None, project: str | None = None,
          port: int = DEFAULT_PORT) -> None:
    import uvicorn

    uvicorn.run(create_app(served, group, project), host="127.0.0.1", port=port, log_level="warning")
