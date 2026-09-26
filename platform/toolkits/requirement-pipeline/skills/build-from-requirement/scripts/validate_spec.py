"""Validate a requirement spec and plan its build against a project.

    uv run python validate_spec.py <spec.yaml> [--project-dir groups/<g>/projects/<p>]
                                               [--json] [--trace]

Exit 0: valid. Exit 1: errors — fix the spec, not the check. Exit 2: valid, but
a blocking open question has no answer — the build does not start.

The checks are the ones `references/requirement-spec.md` marks (checked): the
same key/currency rules `validate_annotations` applies to a dlt resource, dbt
layer naming, every metric and report resolving to a definition, every business
rule and acceptance criterion executable. With `--project-dir` each artefact is
also marked create / reuse / modify against what the project already has, and
the phases to run follow from that.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

SNAKE = re.compile(r"^[a-z][a-z0-9_]*$")
PASCAL = re.compile(r"^[A-Z][A-Za-z0-9]*$")
DURATION = re.compile(r"^\d+[mhd]$")
KINDS = {"rest_api", "sql_database", "filesystem"}
DISPOSITIONS = {"append", "merge", "replace"}
RULE_LAYERS = {"staging", "intermediate", "mart", "metric"}
#: `choose-a-test`'s vocabulary, cheapest first, plus the two non-test proofs.
RULE_TESTS = {
    "data_test": "add-tests",
    "expectation": "add-expectations",
    "unit_test": "add-unit-test",
    "anomaly_monitor": "add-anomaly-tests",
    "contract": "contracts-and-access",
    "metric_filter": "build-semantic-layer",
}
#: Dialects whose SQL runs unchanged here; anything else goes through `pf dialect`.
PORTABLE_DIALECTS = {"duckdb", "ansi", "dbt"}
METRIC_TYPES = {"simple", "ratio", "derived", "cumulative", "conversion"}
MART_PREFIX = {"fact": "fct_", "dimension": "dim_", "report": "rpt_"}
ISO_CURRENCY = re.compile(r"^[A-Z]{3}$")
#: What a metric's number is, so a report can format it. A currency is its ISO
#: code; everything else is one of these. Without it the report guesses, and a
#: volume ends up printed as dollars.
UNITS = {"count", "percent", "ratio", "number", "duration"}
#: Column-name words for a *level* — a balance, a stock, a position — which is
#: counted once per period when summed over time.
STOCK_WORDS = re.compile(
    r"(balance|inventory|on_hand|outstanding|open_interest|headcount|stock_level|backlog|position|aum|exposure)",
    re.I)
SECRET_KEY = re.compile(r"(token|password|passwd|secret|api_?key|private_?key|credential)", re.I)
SECRET_VALUE = re.compile(
    r"(Bearer\s+\S{8,}|sk_(live|test)_\w+|AKIA[0-9A-Z]{16}|xox[abp]-[\w-]+|ghp_\w{20,}|-----BEGIN)")

#: Phase numbers as SKILL.md names them.
PHASES = {
    "scope": 0, "intake": 1, "spec": 2, "impact": 3, "raw": 4, "staging": 5,
    "intermediate": 6, "marts": 7, "metrics": 8, "build": 9,
    "orchestration": 10, "reporting": 11, "catalogue": 12, "close": 13,
}

#: The toolkit skills (and power-tools agents) each phase routes to — the same
#: routing as references/skill-map.md, printed with the plan so the agent sees
#: who owns each step. Raw is resolved per source kind in `skills_for`.
SKILLS: dict[int, list[str]] = {
    0: ["read-memories", "design-architecture", "scaffold-project", "quality-stack"],
    1: [],
    2: ["answer-with-metrics", "design-ontology", "steward-ontology", "choose-a-test"],
    3: ["recce-review", "blast-radius"],
    4: ["find-source", "annotate-source", "setup-data-quality", "debug-pipeline", "steward-ontology"],
    5: ["using-dbt", "quality-stack"],
    6: ["using-dbt", "choose-a-test", "sql-reviewer"],
    7: ["using-dbt", "contracts-and-access", "add-tests", "add-expectations", "sql-reviewer"],
    8: ["build-semantic-layer", "answer-with-metrics", "semantic-conformance"],
    9: ["run-commands", "troubleshoot-runs", "triage-observability", "answer-with-metrics"],
    10: ["build-assets", "dignified-python"],
    11: ["build-dashboard", "charts-and-diagrams", "dashboard-loop"],
    12: ["design-ontology"],
    13: ["recce-review", "impact-verifier", "secrets-auditor", "ship"],
}
KIND_SKILL = {
    "rest_api": "create-rest-pipeline",
    "sql_database": "create-sql-pipeline",
    "filesystem": "create-filesystem-pipeline",
}


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.blocking: list[str] = []
        self.plan: list[dict] = []

    def err(self, where: str, msg: str) -> None:
        self.errors.append(f"{where}: {msg}")

    def warn(self, where: str, msg: str) -> None:
        self.warnings.append(f"{where}: {msg}")


def _list(value) -> list:
    return value if isinstance(value, list) else []


def _dict(value) -> dict:
    return value if isinstance(value, dict) else {}


# ------------------------------------------------------------- the project ----
def _yaml(path: Path) -> dict:
    try:
        return _dict(yaml.safe_load(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return {}


def empty_inventory() -> dict[str, set[str]]:
    return {"models": set(), "metrics": set(), "labels": set(), "sources": set(), "raw": set(), "seeds": set()}


def scan_project(project_dir: Path) -> dict[str, set[str]]:
    """What exists already, each layer from its own evidence.

    * ``raw`` — ``<source>.<resource>`` pairs the project lands: the exported dlt
      annotations (``contracts/annotations.yaml``) and every dbt ``sources:``
      declaration. Never inferred from staging, which can exist without them.
    * ``models`` — dbt model files; ``seeds`` — seed files (a seed can be the
      catalogue a per-entity schedule fans out over).
    * ``metrics`` / ``labels`` — MetricFlow metric names and their labels; a
      label must be unique across the whole semantic manifest.
    """
    inv = empty_inventory()
    transform = project_dir / "transform"
    models_dir = transform / "models"
    if models_dir.is_dir():
        inv["models"] = {p.stem for p in models_dir.rglob("*.sql")}
        for yml in [*models_dir.rglob("*.yml"), *models_dir.rglob("*.yaml")]:
            doc = _yaml(yml)
            for m in _list(doc.get("metrics")):
                m = _dict(m)
                if m.get("name"):
                    inv["metrics"].add(str(m["name"]))
                if m.get("label"):
                    inv["labels"].add(str(m["label"]).casefold())
            for src in _list(doc.get("sources")):
                src = _dict(src)
                for t in _list(src.get("tables")):
                    if src.get("name") and _dict(t).get("name"):
                        inv["raw"].add(f"{src['name']}.{t['name']}")
        staging = models_dir / "staging"
        if staging.is_dir():
            inv["sources"] = {p.name for p in staging.iterdir() if p.is_dir()}
    seeds = transform / "seeds"
    if seeds.is_dir():
        inv["seeds"] = {p.stem for p in seeds.rglob("*.csv")}
    for r in _list(_yaml(project_dir / "contracts" / "annotations.yaml").get("resources")):
        r = _dict(r)
        if r.get("source") and r.get("resource"):
            inv["raw"].add(f"{r['source']}.{r['resource']}")
    inv["sources"] |= {k.split(".", 1)[0] for k in inv["raw"]}
    return inv


# ------------------------------------------------------------------ checks ----
def check_secrets(node, path: str, rep: Report) -> None:
    if isinstance(node, dict):
        for k, v in node.items():
            here = f"{path}.{k}" if path else str(k)
            if k != "secret_ref" and SECRET_KEY.search(str(k)) and isinstance(v, str) and v.strip():
                rep.err(here, "looks like a credential — reference it by name in `secret_ref`, never inline")
            check_secrets(v, here, rep)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            check_secrets(v, f"{path}[{i}]", rep)
    elif isinstance(node, str) and SECRET_VALUE.search(node):
        rep.err(path, "contains what looks like a live credential — remove it and have it rotated")


def check_requirement(spec: dict, rep: Report) -> None:
    req = _dict(spec.get("requirement"))
    if not re.match(r"^REQ-[\w-]+$", str(req.get("id") or "")):
        rep.err("requirement.id", "must look like REQ-<page id or key>")
    if not req.get("title"):
        rep.err("requirement.title", "required")
    if req.get("status") not in {"draft", "confirmed"}:
        rep.err("requirement.status", "draft | confirmed")
    target = _dict(spec.get("target"))
    for k in ("group", "project"):
        if not target.get(k):
            rep.err(f"target.{k}", "required — the build happens in exactly one project")
    for c in _list(spec.get("concepts")):
        name = _dict(c).get("name")
        if not name or not PASCAL.match(str(name)):
            rep.err(f"concepts[{name}]", "concept names are PascalCase ontology classes")
        elif c.get("exists") is False:
            rep.warn(f"concepts[{name}]", "not in the ontology — design-ontology runs before any model")


def check_sources(spec: dict, rep: Report) -> set[str]:
    staged: set[str] = set()
    for s in _list(spec.get("sources")):
        s = _dict(s)
        name = str(s.get("name") or "")
        where = f"sources[{name or '?'}]"
        if not SNAKE.match(name):
            rep.err(where, "name must be snake_case — it becomes the raw dataset")
        if s.get("kind") not in KINDS:
            rep.err(where, f"kind must be one of {sorted(KINDS)}")
        for k, v in _dict(s.get("freshness")).items():
            if v is not None and not DURATION.match(str(v)):
                rep.err(f"{where}.freshness.{k}", "use <n>m | <n>h | <n>d")
        if not _list(s.get("resources")):
            rep.err(where, "at least one resource")
        for r in _list(s.get("resources")):
            r = _dict(r)
            rname = str(r.get("name") or "")
            rw = f"{where}.resources[{rname or '?'}]"
            if not SNAKE.match(rname):
                rep.err(rw, "name must be snake_case")
            if not any(r.get(k) for k in ("endpoint", "table", "glob")):
                rep.err(rw, "needs endpoint, table or glob")
            disp = r.get("write_disposition")
            if disp not in DISPOSITIONS:
                rep.err(rw, f"write_disposition must be one of {sorted(DISPOSITIONS)}")
            if disp == "merge" and not r.get("primary_key"):
                rep.err(rw, "merge needs primary_key")
            if not r.get("concept"):
                rep.err(rw, "concept required — annotate-source cannot run without it")
            if not r.get("grain"):
                rep.err(rw, "grain required, in words")
            roles = _dict(r.get("roles"))
            keys = [c for c, role in roles.items() if role == "natural_key"]
            if len(keys) != 1:
                rep.err(rw, f"exactly one natural_key role, found {len(keys)}")
            currency = r.get("currency")
            if currency is not None and not ISO_CURRENCY.match(str(currency)):
                rep.err(rw, f"currency {currency!r} is not an ISO 4217 code")
            if "money_amount" in roles.values() and "currency_code" not in roles.values() and not currency:
                rep.err(rw, "a money_amount needs a sibling currency_code, or `currency: <ISO>` "
                            "when every amount is in one currency")
            staged.add(f"stg_{name}__{rname}")
    return staged


def check_rules(spec: dict, rep: Report, defined: set[str]) -> set[str]:
    ids: set[str] = set()
    for r in _list(spec.get("business_rules")):
        r = _dict(r)
        rid = str(r.get("id") or "")
        where = f"business_rules[{rid or '?'}]"
        if not re.match(r"^BR-\d+$", rid):
            rep.err(where, "id must be BR-<n>")
        if rid in ids:
            rep.err(where, "duplicate id")
        ids.add(rid)
        if not r.get("statement"):
            rep.err(where, "statement required — the page's own wording")
        if r.get("layer") not in RULE_LAYERS:
            rep.err(where, f"layer must be one of {sorted(RULE_LAYERS)}")
        impl = _list(r.get("implemented_in"))
        if not impl:
            rep.err(where, "implemented_in is empty — a rule nothing implements is not built")
        for n in impl:
            if n not in defined:
                rep.err(where, f"implemented_in names {n!r}, which the spec does not define")
        test = _dict(r.get("test"))
        if test.get("type") not in RULE_TESTS:
            rep.err(where, f"test.type must be one of {sorted(RULE_TESTS)} — a rule nobody checks breaks unnoticed")
        elif test["type"] == "anomaly_monitor":
            rep.warn(where, "an anomaly monitor is statistical and cannot prove a rule alone — "
                            "choose-a-test: add a data_test, expectation or unit_test beside it")
        elif test["type"] == "metric_filter" and r.get("layer") != "metric":
            rep.err(where, "metric_filter proves only a rule whose layer is metric")
        ref = _dict(r.get("reference_sql"))
        if ref and str(ref.get("dialect") or "").lower() not in PORTABLE_DIALECTS:
            rep.warn(where, f"reference_sql is {ref.get('dialect') or 'an unknown dialect'} — "
                            "port-snowflake-sql: run `pf dialect`, never translate an ambiguous function")
    return ids


def check_models(spec: dict, rep: Report, known: set[str], rule_ids: set[str]) -> None:
    models = _dict(spec.get("models"))
    seen: set[str] = set()
    for m in [*_list(models.get("intermediate")), *_list(models.get("marts"))]:
        name = str(_dict(m).get("name") or "")
        if name and name in seen:
            rep.err(f"models[{name}]", "defined twice — dbt refuses two models with one name")
        seen.add(name)
    for m in _list(models.get("intermediate")):
        m = _dict(m)
        name = str(m.get("name") or "")
        where = f"models.intermediate[{name or '?'}]"
        if not re.match(r"^int_[a-z0-9_]+__[a-z0-9_]+$", name):
            rep.err(where, "name must be int_<entity>__<verb>")
        _check_inputs(m, where, rep, known)
        _check_rule_refs(m, where, rep, rule_ids)
    for m in _list(models.get("marts")):
        m = _dict(m)
        name = str(m.get("name") or "")
        where = f"models.marts[{name or '?'}]"
        prefix = MART_PREFIX.get(str(m.get("kind")))
        if prefix is None:
            rep.err(where, f"kind must be one of {sorted(MART_PREFIX)}")
        elif not name.startswith(prefix) or not SNAKE.match(name):
            rep.err(where, f"a {m.get('kind')} mart is named {prefix}<snake_case>")
        if not m.get("grain"):
            rep.err(where, "grain required — the mart declares it, the metric aggregates it")
        _check_inputs(m, where, rep, known)
        _check_rule_refs(m, where, rep, rule_ids)
        cols = _list(m.get("columns"))
        if cols and sum(1 for c in cols if _dict(c).get("role") == "natural_key") != 1:
            rep.err(where, "exactly one natural_key column")


def _check_inputs(m: dict, where: str, rep: Report, known: set[str]) -> None:
    inputs = _list(m.get("inputs"))
    if not inputs:
        rep.err(where, "inputs required")
    for i in inputs:
        if i not in known:
            rep.err(where, f"input {i!r} is neither defined in the spec nor in the project")


def _check_rule_refs(item: dict, where: str, rep: Report, rule_ids: set[str]) -> None:
    for r in _list(item.get("rules")):
        if r not in rule_ids:
            rep.err(where, f"rule {r!r} is not in business_rules")


def _money_columns(spec: dict) -> dict[str, set[str]]:
    """{mart: its money_amount columns}, from the spec's mart columns."""
    out: dict[str, set[str]] = {}
    for m in _list(_dict(spec.get("models")).get("marts")):
        m = _dict(m)
        out[str(m.get("name"))] = {str(_dict(c).get("name")) for c in _list(m.get("columns"))
                                   if _dict(c).get("role") == "money_amount"}
    return out


def check_metrics(spec: dict, rep: Report, marts: set[str], existing: dict[str, set[str]],
                  rule_ids: set[str]) -> set[str]:
    existing_names, existing_labels = existing["metrics"], existing["labels"]
    items = [_dict(m) for m in _list(spec.get("metrics"))]
    names = {str(m.get("name")) for m in items}
    resolvable = names | existing_names
    money = _money_columns(spec)
    seen_names: set[str] = set()
    seen_labels: set[str] = set()
    for m in items:
        name = str(m.get("name") or "")
        where = f"metrics[{name or '?'}]"
        if not SNAKE.match(name):
            rep.err(where, "name must be snake_case")
        if name in seen_names:
            rep.err(where, "defined twice")
        seen_names.add(name)
        label = str(m.get("label") or "")
        if not label:
            rep.err(where, "label required — the business's own words")
        elif label.casefold() in seen_labels or (label.casefold() in existing_labels and name not in existing_names):
            rep.err(where, f"label {label!r} is already used — MetricFlow requires labels unique across "
                           "the semantic manifest; qualify it (e.g. by grain)")
        seen_labels.add(label.casefold())
        unit = m.get("unit")
        if not unit:
            rep.err(where, f"unit required — an ISO currency code or one of {sorted(UNITS)}; "
                           "the report formats the number from it")
        elif unit not in UNITS and not ISO_CURRENCY.match(str(unit)):
            rep.err(where, f"unit {unit!r} is neither an ISO currency code nor one of {sorted(UNITS)}")
        kind = m.get("type")
        if kind not in METRIC_TYPES:
            rep.err(where, f"type must be one of {sorted(METRIC_TYPES)}")
        if kind in {"simple", "cumulative"}:
            if m.get("mart") not in marts:
                rep.err(where, f"mart {m.get('mart')!r} is not a mart in the spec or project")
            measure = _dict(m.get("measure"))
            if not measure.get("agg") or not measure.get("expr"):
                rep.err(where, "measure needs agg and expr")
            if "/" in str(measure.get("expr") or ""):
                rep.err(where, "a measure that divides is avg(ratio) waiting to happen — make it a ratio metric")
            averaged_rate = re.search(r"(rate|ratio|pct|percent|share)", str(measure.get("expr")))
            if measure.get("agg") in {"average", "avg"} and averaged_rate:
                rep.err(where, "averaging a rate — compose a ratio of its numerator and denominator")
            expr = str(measure.get("expr") or "")
            if (measure.get("agg") == "sum" and STOCK_WORDS.search(expr)
                    and not _dict(measure.get("non_additive")).get("dimension")):
                rep.warn(where, f"{expr!r} reads like a level (a balance, a position), not a flow — summed over "
                                "time it is counted once per period; declare measure.non_additive "
                                "{dimension: <time>, window: last} or confirm it is a flow")
            if expr in money.get(str(m.get("mart")), set()) and unit and not ISO_CURRENCY.match(str(unit)):
                rep.err(where, f"measures money column {expr!r} but unit is {unit!r} — use its currency code")
        elif kind == "ratio":
            for part in ("numerator", "denominator"):
                if m.get(part) not in resolvable:
                    rep.err(where, f"{part} {m.get(part)!r} is not a defined or existing metric")
        elif kind == "derived":
            if not m.get("expr"):
                rep.err(where, "derived needs expr")
            for dep in _list(m.get("metrics")):
                if dep not in resolvable:
                    rep.err(where, f"depends on unknown metric {dep!r}")
        _check_rule_refs(m, where, rep, rule_ids)
        if name in existing_names and m.get("action") != "modify":
            rep.warn(where, "already exists in the project — reuse it (drop it from the spec) or set action: modify")
    return names


def check_reports(spec: dict, rep: Report, metrics: set[str]) -> None:
    pages: set[str] = set()
    for r in _list(spec.get("reports")):
        r = _dict(r)
        page = str(r.get("page") or "")
        where = f"reports[{page or '?'}]"
        if not re.match(r"^[a-z0-9][a-z0-9-]*$", page):
            rep.err(where, "page must be a kebab-case slug")
        if page in pages:
            rep.err(where, "duplicate page")
        pages.add(page)
        if not r.get("question"):
            rep.err(where, "question required — one page answers one question")
        per = r.get("per_entity")
        if per is not None and not SNAKE.match(str(per)):
            rep.err(where, "per_entity names the dimension a page is templated over (snake_case), "
                           "e.g. `region` → reporting/pages/<page>/[region].md")
        if not _list(r.get("metrics")):
            rep.err(where, "a page with no metric restates business logic in SQL")
        for m in _list(r.get("metrics")):
            if m not in metrics:
                rep.err(where, f"metric {m!r} is not defined or existing")


def check_acceptance(spec: dict, rep: Report, metrics: set[str]) -> None:
    acs = _list(spec.get("acceptance"))
    if not acs:
        rep.err("acceptance", "at least one criterion — a requirement with nothing to accept cannot be finished")
    for a in acs:
        a = _dict(a)
        aid = str(a.get("id") or "")
        where = f"acceptance[{aid or '?'}]"
        if not re.match(r"^AC-\d+$", aid):
            rep.err(where, "id must be AC-<n>")
        check = _dict(a.get("check"))
        if "metric" in check:
            if check["metric"] not in metrics:
                rep.err(where, f"metric {check['metric']!r} is not defined or existing")
            if not _dict(check.get("expect")):
                rep.err(where, "a metric check needs expect: equals | between | reconciles_to")
        elif "manual" in check:
            rep.warn(where, "manual sign-off — reported as not automated")
        elif "test" not in check:
            rep.err(where, "check must be {metric, grain, expect} | {test} | {manual}")


def check_schedule(spec: dict, rep: Report, known: set[str]) -> None:
    """`schedule.per_entity`: one job per entity (a customer, a market, a
    store), each paused or resumed on its own. The entity list is a catalogue
    the loader and dbt both read, so the two can never disagree."""
    sched = _dict(spec.get("schedule"))
    per = sched.get("per_entity")
    if per is None:
        return
    per = _dict(per)
    where = "schedule.per_entity"
    if not SNAKE.match(str(per.get("by") or "")):
        rep.err(where, "by: the entity column (snake_case) the jobs fan out over")
    catalogue = str(per.get("catalogue") or "")
    if not SNAKE.match(catalogue):
        rep.err(where, "catalogue: the seed or model listing every entity — loader and dbt read the same list")
    elif catalogue not in known:
        rep.warn(where, f"catalogue {catalogue!r} is not a seed or model yet — it is created in Phase 4")
    stagger = per.get("stagger")
    if stagger is not None and not DURATION.match(str(stagger)):
        rep.err(f"{where}.stagger", "use <n>m | <n>h")
    if not (sched.get("cron") or sched.get("trigger")):
        rep.err(where, "a per-entity job still needs schedule.cron or schedule.trigger")
    for e in _list(per.get("start_paused")):
        if not isinstance(e, str) or not e:
            rep.err(f"{where}.start_paused", "entity keys, as strings")


def check_questions(spec: dict, rep: Report) -> None:
    for q in _list(spec.get("open_questions")):
        q = _dict(q)
        if q.get("blocking") and not q.get("answer"):
            rep.blocking.append(f"{q.get('id')}: {q.get('question')} (ask: {q.get('ask') or 'owner'})")


# -------------------------------------------------------------------- plan ----
def build_plan(spec: dict, existing: dict[str, set[str]], rep: Report) -> None:
    def mark(layer: str, name: str, present: bool, item: dict | None = None) -> None:
        action = (item or {}).get("action") or ("modify" if present else "create")
        rep.plan.append({"layer": layer, "name": name, "action": action})

    for s in _list(spec.get("sources")):
        s = _dict(s)
        for r in _list(s.get("resources")):
            raw = f"{s.get('name')}.{_dict(r).get('name')}"
            stg = f"stg_{s.get('name')}__{_dict(r).get('name')}"
            # Each layer on its own evidence: a staging model without a landed
            # resource behind it still needs the pipeline built.
            rep.plan.append({"layer": "raw", "name": raw,
                             "action": "reuse" if raw in existing.get("raw", set()) else "create"})
            rep.plan.append({"layer": "staging", "name": stg,
                             "action": "reuse" if stg in existing["models"] else "create"})
    models = _dict(spec.get("models"))
    for layer, key in (("intermediate", "intermediate"), ("marts", "marts")):
        for m in _list(models.get(key)):
            m = _dict(m)
            mark(layer, str(m.get("name")), m.get("name") in existing["models"], m)
    for m in _list(spec.get("metrics")):
        m = _dict(m)
        present = m.get("name") in existing["metrics"]
        rep.plan.append({"layer": "metrics", "name": str(m.get("name")),
                         "action": m.get("action") or ("reuse" if present else "create")})
    for r in _list(spec.get("reports")):
        rep.plan.append({"layer": "reporting", "name": str(_dict(r).get("page")), "action": "create"})
    per = _dict(_dict(spec.get("schedule")).get("per_entity"))
    if per.get("by"):
        rep.plan.append({"layer": "orchestration", "name": f"one job per {per['by']} ({per.get('catalogue')})",
                         "action": "create"})


def phases(rep: Report, spec: dict) -> list[int]:
    touched = {p["layer"] for p in rep.plan if p["action"] in {"create", "modify"}}
    run = {"scope", "intake", "spec", "build", "catalogue", "close"}
    if any(p["action"] == "modify" for p in rep.plan):
        run.add("impact")
    run |= touched & set(PHASES)
    schedule = _dict(spec.get("schedule"))
    if (schedule.get("cron") or schedule.get("trigger")) and touched & {"raw", "marts"}:
        run.add("orchestration")
    if "orchestration" in touched:
        run.add("orchestration")
    if not touched & {"raw", "staging", "intermediate", "marts", "metrics"}:
        run.discard("build")
    return sorted(PHASES[p] for p in run)


def skills_for(phase: int, spec: dict, modifying: bool = False) -> list[str]:
    """The skills a phase routes to for *this* spec: the fixed routing, plus the
    ones the spec's own content calls for (a source kind, a rule's test type, a
    sample file, SQL from another dialect). The diff review at close runs only
    when something existing is being modified — there is no baseline otherwise."""
    out = list(SKILLS.get(phase, []))
    if phase == 13 and not modifying:
        out = [n for n in out if n not in {"recce-review", "impact-verifier"}]
    sources = [_dict(s) for s in _list(spec.get("sources"))]
    rules = [_dict(r) for r in _list(spec.get("business_rules"))]

    def add(*names: str) -> None:
        out.extend(n for n in names if n not in out)

    if phase == 2 and any(s.get("sample") for s in sources):
        add("read-file")
    if phase == 4:
        add(*(KIND_SKILL[s["kind"]] for s in sources if s.get("kind") in KIND_SKILL))
        if any(s.get("kind") == "filesystem" for s in sources):
            add("read-file")
        if any(_dict(s.get("connection")).get("secret_ref") for s in sources):
            add("secrets-auditor")
        if _dict(spec.get("schedule")).get("sla"):
            add("optimize-performance")
        add("dignified-python")
    if phase in (6, 7):
        layer = "intermediate" if phase == 6 else "mart"
        for r in rules:
            if r.get("layer") == layer:
                add(RULE_TESTS.get(_dict(r.get("test")).get("type"), ""))
        if phase == 6 and any(_dict(r.get("reference_sql")) for r in rules):
            add("port-snowflake-sql")
        if phase == 7 and any(_dict(s.get("freshness")) for s in sources):
            add("add-anomaly-tests")
    return [n for n in out if n]


def trace(spec: dict) -> str:
    """The skeleton of requirements/<REQ>/trace.md — filled in at Phase 13."""
    req = _dict(spec.get("requirement"))
    lines = [f"# {req.get('id')} — {req.get('title')}", "",
             f"Source: {_dict(req.get('source')).get('url')} (version {_dict(req.get('source')).get('version')})", "",
             "| Item | Statement | Implemented in | Proven by | Result |", "|---|---|---|---|---|"]
    for r in _list(spec.get("business_rules")):
        r = _dict(r)
        lines.append(f"| {r.get('id')} | {r.get('statement')} | {', '.join(_list(r.get('implemented_in')))} "
                     f"| {_dict(r.get('test')).get('type')} | |")
    for m in _list(spec.get("metrics")):
        m = _dict(m)
        lines.append(f"| metric `{m.get('name')}` | {m.get('description') or m.get('label')} | "
                     "transform/models/semantic/ | query_metrics | |")
    for p in _list(spec.get("reports")):
        p = _dict(p)
        path = (f"reporting/pages/{p.get('page')}/[{p['per_entity']}].md" if p.get("per_entity")
                else f"reporting/pages/{p.get('page')}.md")
        lines.append(f"| page `{p.get('page')}` | {p.get('question')} | {path} "
                     "| pf report audit, rendered and looked at | |")
    for a in _list(spec.get("acceptance")):
        a = _dict(a)
        lines.append(f"| {a.get('id')} | {a.get('statement')} | — | {json.dumps(a.get('check'))} | |")
    return "\n".join(lines) + "\n"


# -------------------------------------------------------------------- main ----
def validate(spec: dict, project_dir: Path | None = None) -> Report:
    rep = Report()
    if not isinstance(spec, dict) or spec.get("spec_version") != 1:
        rep.err("spec_version", "must be 1")
        return rep
    if project_dir:
        project_dir = project_dir.resolve()
    existing = scan_project(project_dir) if project_dir else empty_inventory()
    if project_dir:
        target = _dict(spec.get("target"))
        if project_dir.name != target.get("project") or project_dir.parent.parent.name != target.get("group"):
            rep.err("target", f"spec targets {target.get('group')}/{target.get('project')}, "
                              f"not {project_dir.parent.parent.name}/{project_dir.name}")

    check_secrets(spec, "", rep)
    check_requirement(spec, rep)
    staged = check_sources(spec, rep)
    models = _dict(spec.get("models"))
    ints = {str(_dict(m).get("name")) for m in _list(models.get("intermediate"))}
    marts = {str(_dict(m).get("name")) for m in _list(models.get("marts"))}
    metric_names = {str(_dict(m).get("name")) for m in _list(spec.get("metrics"))}
    known_models = staged | ints | marts | existing["models"]
    rule_ids = check_rules(spec, rep, known_models | metric_names | existing["metrics"])
    check_models(spec, rep, known_models, rule_ids)
    metrics = check_metrics(spec, rep, marts | existing["models"], existing, rule_ids) | existing["metrics"]
    check_reports(spec, rep, metrics)
    check_acceptance(spec, rep, metrics)
    check_schedule(spec, rep, known_models | existing["seeds"])
    check_questions(spec, rep)
    build_plan(spec, existing, rep)
    return rep


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", type=Path)
    ap.add_argument("--project-dir", type=Path)
    ap.add_argument("--json", action="store_true", help="machine-readable report")
    ap.add_argument("--trace", action="store_true", help="print the trace.md skeleton and exit")
    args = ap.parse_args(argv)

    try:
        spec = yaml.safe_load(args.spec.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        print(f"✗ {args.spec}: {exc}")
        return 1
    if args.trace:
        print(trace(spec), end="")
        return 0
    rep = validate(spec, args.project_dir)
    run = phases(rep, spec) if not rep.errors else []
    modifying = any(p["action"] == "modify" for p in rep.plan)
    routing = {p: skills_for(p, spec, modifying) for p in run}
    code = 1 if rep.errors else 2 if rep.blocking else 0

    if args.json:
        print(json.dumps({"errors": rep.errors, "warnings": rep.warnings, "blocking": rep.blocking,
                          "plan": rep.plan, "phases": run, "routing": routing, "exit": code}, indent=2))
        return code

    for e in rep.errors:
        print(f"✗ {e}")
    for w in rep.warnings:
        print(f"! {w}")
    for b in rep.blocking:
        print(f"? blocking {b}")
    if rep.plan:
        print(f"plan[{len(rep.plan)}]{{layer,name,action}}:")
        for p in rep.plan:
            print(f"  {p['layer']},{p['name']},{p['action']}")
    if run:
        print(f"phases[{len(run)}]{{phase,skills}}:")
        for p in run:
            print(f"  {p},{' '.join(routing[p]) or '-'}")
    print({0: "✓ valid", 1: f"✗ {len(rep.errors)} error(s)", 2: "✓ valid — blocked on open questions"}[code])
    return code


if __name__ == "__main__":
    sys.exit(main())
