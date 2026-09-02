"""The metric-question surface: a business question, answered from governed metrics.

"Why did EU revenue drop in July?" is the 80% case of analytics, and the one
this platform had no front door for. The semantic layer exists, Evidence renders
it, Wren serves it over MCP — and a person still had to know a metric's name to
get a number. This is the agent that takes the question instead.

## The constraint that makes it safe to give to a business user

The agent has exactly three tools — `list_metrics`, `get_dimensions`,
`query_metrics` — and no SQL. It cannot reach a table. Every number it returns
came through a MetricFlow metric, which means it came through a definition that
was reviewed in a pull request, with its filter, its grain and its time column
already decided. An answer is therefore *the metric's* answer, and the response
says which metric, which dimensions and which filter produced it, with a link
to the governed page that shows the same number.

When no metric covers the question, the correct answer is "no metric covers
this — the fix is a metric PR", not a guess from a table. That is the same rule
the reporting layer enforces on pages, applied to a conversation.

## Two paths

  * **live** — a tool-use loop on the routed model (`metric_answerer`), ending
    with a typed `Answer`. Bounded: at most `MAX_TURNS` tool calls, every call
    billed through `pf.obs` like any loop step.
  * **direct** — no credentials, or `--direct`. A deterministic parser for the
    shape `<metric> [by <dimension>] [where <filter>]`. It answers the questions
    a dashboard filter could, and refuses the rest honestly.

Delivery is separate (`pf.notify`): the same `Answer` posts to a Slack channel
per group, prints in a terminal, or comes back over MCP.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from pf.agents.base import AGENTS, NoCredentials, cached_prefix, client, have_credentials
from pf.agents.models import request_params

MAX_TURNS = 8
MAX_ROWS = 50


# --------------------------------------------------------------- schema ----
class Answer(BaseModel):
    understanding: str = Field(
        default="", description="What you took the question to mean — the metric, "
                                "period and comparison implied — before answering.")
    plan: list[str] = Field(
        default_factory=list,
        description="The tool calls you made and why, one line each.")
    answer: str = Field(description="The answer in plain language, two to five sentences.")
    metrics: list[str] = Field(description="Metric names used. Empty if none covered it.")
    group_by: list[str] = Field(default_factory=list)
    where: str = ""
    covered: bool = Field(description="False if no governed metric answers the question.")
    missing_definition: str = Field(
        default="", description="If not covered: the metric that would need to exist.")
    caveats: list[str] = Field(default_factory=list)


@dataclass
class Result:
    question: str
    answer: Answer
    rows: list[dict[str, Any]] = field(default_factory=list)
    page: str = ""
    path: str = "live"     # live | direct
    tokens: int = 0
    turns: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {"question": self.question, "answer": self.answer.model_dump(),
                "rows": self.rows[:MAX_ROWS], "page": self.page, "path": self.path,
                "tokens": self.tokens, "turns": self.turns}

    def render(self) -> str:
        a = self.answer
        lines = [a.answer, ""]
        if a.metrics:
            lines.append(f"metric: {', '.join(a.metrics)}"
                         + (f" · by {', '.join(a.group_by)}" if a.group_by else "")
                         + (f" · where {a.where}" if a.where else ""))
        if self.page:
            lines.append(f"governed page: {self.page}")
        if not a.covered and a.missing_definition:
            lines.append(f"no metric covers this — needs: {a.missing_definition}")
        for c in a.caveats:
            lines.append(f"caveat: {c}")
        return "\n".join(lines)


# ------------------------------------------------------- semantic tools ----
def metrics_catalogue(pdir: Path) -> list[dict[str, Any]]:
    sm = pdir / "transform" / "target" / "semantic_manifest.json"
    if not sm.exists():
        return []
    payload = json.loads(sm.read_text(encoding="utf-8"))
    return [{"name": m["name"], "type": m.get("type"),
             "label": m.get("label") or "", "description": m.get("description") or ""}
            for m in payload.get("metrics") or []]


def dimensions_for(pdir: Path, metrics: list[str]) -> str:
    from pf.runtime.dbt_runtime import mf
    proc = mf(pdir, "list", "dimensions", "--metrics", ",".join(metrics))
    return (proc.stdout or proc.stderr)[:4000]


def query(pdir: Path, metrics: list[str], group_by: list[str] | None = None,
          where: str = "", limit: int = MAX_ROWS) -> tuple[bool, str, list[dict[str, Any]]]:
    from pf.runtime.dbt_runtime import mf_query
    group_by = group_by or []
    proc = mf_query(pdir, metrics, group_by, where, min(limit, MAX_ROWS))
    if proc.returncode != 0:
        return False, _clean(proc.stderr or proc.stdout)[:2000], []
    text = _clean(proc.stdout)
    rows = _parse_table(text)
    # Time series read in order; mf returns them in hash order.
    time_cols = [g for g in group_by if g.startswith("metric_time__")]
    if time_cols and rows and all(time_cols[0] in r for r in rows):
        rows.sort(key=lambda r: r[time_cols[0]])
        text = _render_table(rows)
    return True, text[:6000], rows


_NOISE = ("Initiating query", "Success", "Warning", "Please update", "pip install",
          "$ ", "💡", "‼", "✔", "✗")


def _clean(text: str) -> str:
    """Drop the CLI's spinner, version nag and success banner; keep the table."""
    out = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s or any(n in s for n in _NOISE) or s in ("-", "\\", "|", "/"):
            continue
        if s[0] in "-\\|/" and "Initiating" in s:
            continue
        out.append(ln.rstrip())
    return "\n".join(out)


def _parse_table(text: str) -> list[dict[str, Any]]:
    """MetricFlow prints a fixed-width table; good enough to make rows of it."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) < 2:
        return []
    header = lines[0].split()
    rows = []
    for ln in lines[1:]:
        if set(ln.strip()) <= set("-+ |"):
            continue
        parts = ln.split()
        if len(parts) == len(header):
            rows.append(dict(zip(header, parts, strict=True)))
    return rows[:MAX_ROWS]


def _render_table(rows: list[dict[str, Any]]) -> str:
    cols = list(rows[0])
    widths = {c: max(len(c), *(len(str(r[c])) for r in rows)) for c in cols}
    head = "  ".join(c.ljust(widths[c]) for c in cols)
    sep = "  ".join("-" * widths[c] for c in cols)
    body = ["  ".join(str(r[c]).ljust(widths[c]) for c in cols) for r in rows]
    return "\n".join([head, sep, *body])


def governed_page(pdir: Path, metric: str) -> str:
    page = pdir / "reporting" / "pages" / "metrics" / f"{metric}.md"
    return f"reporting/pages/metrics/{metric}.md" if page.exists() else ""


# ---------------------------------------------------------------- direct ----
_DIRECT = re.compile(
    r"^\s*(?:what(?:'s| is| was)?\s+)?(?:the\s+)?(?P<metric>[a-z0-9_]+)"
    r"(?:\s+by\s+(?P<dim>[a-z0-9_]+(?:__[a-z0-9_]+)?))?"
    r"(?:\s+where\s+(?P<where>.+?))?\s*\??\s*$", re.IGNORECASE)


def answer_direct(pdir: Path, question: str) -> Result:
    """No model. Exact metric name, optional `by`, optional `where`."""
    cat = {m["name"]: m for m in metrics_catalogue(pdir)}
    m = _DIRECT.match(question.replace("-", "_"))
    if not m or m.group("metric").lower() not in cat:
        names = ", ".join(sorted(cat)) or "(no metrics defined)"
        return Result(question, Answer(
            answer=f"I can only answer directly in the form `<metric> [by <dimension>]`. "
                   f"Governed metrics here: {names}.",
            metrics=[], covered=False, missing_definition="", caveats=[]), path="direct")
    metric = m.group("metric").lower()
    dim = m.group("dim")
    group_by = [resolve_dimension(pdir, metric, dim)] if dim else []
    where = m.group("where") or ""
    ok, text, rows = query(pdir, [metric], group_by, where)
    if not ok:
        return Result(question, Answer(
            answer=f"MetricFlow could not run `{metric}`: {text[:300]}",
            metrics=[metric], group_by=group_by, where=where, covered=True,
            caveats=["query failed"]), path="direct")
    head = "\n".join(text.splitlines()[:26])
    more = f"\n… {len(rows) - 24} more row(s)" if len(rows) > 24 else ""
    return Result(question, Answer(
        understanding=f"direct: metric `{metric}`"
                      + (f" by {', '.join(group_by)}" if group_by else "")
                      + (f" where {where}" if where else ""),
        answer=f"`{metric}`" + (f" by {', '.join(group_by)}" if group_by else "")
               + f":\n{head}{more}", metrics=[metric], group_by=group_by, where=where,
        covered=True), rows=rows, page=governed_page(pdir, metric), path="direct")


_TIME_GRAINS = ("day", "week", "month", "quarter", "year")


def resolve_dimension(pdir: Path, metric: str, dim: str) -> str:
    """`plan_tier` -> `payment__plan_tier`; `month` -> `metric_time__month`.

    MetricFlow wants the entity-qualified name. A person does not know the
    entity, and should not have to: if exactly one available dimension ends in
    `__<dim>`, that is the one. Ambiguity or no match passes the name through
    and lets MetricFlow say so.
    """
    d = dim.lower()
    if "__" in d:
        return d
    if d in _TIME_GRAINS:
        return f"metric_time__{d}"
    listed = dimensions_for(pdir, [metric])
    names = [ln.strip().lstrip("•").strip() for ln in listed.splitlines()
             if "__" in ln and not ln.strip().startswith(("✔", "✗", "-"))]
    hits = [n for n in names if n.endswith(f"__{d}")]
    return hits[0] if len(hits) == 1 else d


# ------------------------------------------------------------------ live ----
TOOLS: list[dict[str, Any]] = [
    {"name": "list_metrics",
     "description": "Every governed metric: name, type, label, description. Start here.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "get_dimensions",
     "description": "Dimensions available for the given metrics (e.g. metric_time__month, "
                    "customer__segment). Call before grouping or filtering.",
     "input_schema": {"type": "object",
                      "properties": {"metrics": {"type": "array", "items": {"type": "string"}}},
                      "required": ["metrics"]}},
    {"name": "query_metrics",
     "description": "Run governed metrics with optional group_by dimensions and a "
                    "MetricFlow `where` filter. The only way to get a number.",
     "input_schema": {"type": "object",
                      "properties": {
                          "metrics": {"type": "array", "items": {"type": "string"}},
                          "group_by": {"type": "array", "items": {"type": "string"}},
                          "where": {"type": "string"},
                          "limit": {"type": "integer"}},
                      "required": ["metrics"]}},
    {"name": "final_answer",
     "description": "Finish. Call exactly once, when you have the answer or have "
                    "established that no metric covers the question.",
     "input_schema": Answer.model_json_schema()},
]

SYSTEM_RULES = (
    "You answer business questions for this company using ONLY its governed metrics.\n"
    "- You have no SQL and no tables. If no metric covers the question, say so in "
    "final_answer with covered=false and name the definition that would be needed. "
    "Never estimate from a different metric and present it as the answer.\n"
    "- Always call list_metrics first, then get_dimensions for the metrics you will "
    "use, then query_metrics. Group by time (metric_time__month etc.) when the "
    "question implies a period or a trend.\n"
    "- For a 'why' question: query the metric by the dimensions most likely to "
    "explain it (at most three queries), and report which segment moved. Do not "
    "speculate beyond what the numbers show; put hypotheses in caveats.\n"
    "- Name the metric, the dimensions and the filter you used. A reader must be "
    "able to reproduce the number from the governed page.\n"
    "- Be brief. Two to five sentences."
)


def _run_tool(pdir: Path, name: str, args: dict[str, Any],
              state: dict[str, Any]) -> str:
    if name == "list_metrics":
        cat = metrics_catalogue(pdir)
        if not cat:
            return "No metrics defined. Run `pf seed` after adding semantic models."
        return "\n".join(f"{m['name']} ({m['type']}) — {m['label'] or m['description']}"
                         for m in cat)
    if name == "get_dimensions":
        return dimensions_for(pdir, list(args.get("metrics") or []))
    if name == "query_metrics":
        metrics = list(args.get("metrics") or [])
        ok, text, rows = query(pdir, metrics, list(args.get("group_by") or []),
                               str(args.get("where") or ""), int(args.get("limit") or MAX_ROWS))
        if ok:
            state["rows"] = rows
            state["last_metrics"] = metrics
        return text if ok else f"MetricFlow error: {text}"
    return f"unknown tool {name}"


def answer_live(root: Path, group: str, project: str, question: str) -> Result:
    """Tool-use loop. Ends with `final_answer` or a bounded-turns caveat."""
    from pf import obs, trace

    if not have_credentials():
        raise NoCredentials("no credential for the metric answerer")
    pdir = root / "groups" / group / "projects" / project
    cfg = AGENTS["metric_answerer"]
    tr = trace.get()
    tr.intent(cfg.purpose, agent=cfg.name, model=cfg.model, question=question)
    system = cached_prefix(root, group, project, cfg)
    system.append({"type": "text", "text": SYSTEM_RULES})
    messages: list[dict[str, Any]] = [{"role": "user", "content": question}]
    params = request_params(cfg.model, effort=cfg.effort, thinking=cfg.thinking,
                            max_tokens=cfg.max_tokens)
    c = client()
    state: dict[str, Any] = {"rows": [], "last_metrics": []}
    tokens, turns, t0 = 0, 0, time.time()
    final: Answer | None = None

    while turns < MAX_TURNS and final is None:
        turns += 1
        if turns == 1:
            tr.request(agent=cfg.name, model=cfg.model, params=params, system=system,
                       user=question, schema="Answer(final_answer tool)")
        resp = c.messages.create(**params, system=system, messages=messages, tools=TOOLS)
        tokens += resp.usage.input_tokens + resp.usage.output_tokens
        tr.event("turn", turn=turns, stop_reason=str(getattr(resp, "stop_reason", "")),
                 usage={"input_tokens": resp.usage.input_tokens,
                        "output_tokens": resp.usage.output_tokens},
                 text="".join(getattr(b, "text", "") for b in resp.content)[:2000])
        if getattr(resp, "stop_reason", None) == "refusal":
            final = Answer(answer="The model declined to answer.", metrics=[],
                           covered=False, caveats=["refusal"])
            break
        messages.append({"role": "assistant", "content": resp.content})
        results: list[dict[str, Any]] = []
        for block in resp.content:
            if getattr(block, "type", "") != "tool_use":
                continue
            if block.name == "final_answer":
                final = Answer.model_validate(block.input)
                tr.response(agent=cfg.name, parsed=final,
                            usage={"input_tokens": tokens, "output_tokens": 0},
                            stop_reason="final_answer", ms=int((time.time() - t0) * 1000))
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": "recorded"})
                continue
            args = dict(block.input or {})
            tr.tool_call(block.name, args, turn=turns)
            out = _run_tool(pdir, block.name, args, state)
            tr.tool_result(block.name, out, turn=turns)
            results.append({"type": "tool_result", "tool_use_id": block.id, "content": out})
        if not results:
            text = "".join(getattr(b, "text", "") for b in resp.content)
            final = Answer(answer=text or "(no answer)", metrics=state["last_metrics"],
                           covered=bool(state["last_metrics"]),
                           caveats=["model ended without final_answer"])
            break
        messages.append({"role": "user", "content": results})

    if final is None:
        final = Answer(answer="Stopped after the turn limit without an answer.",
                       metrics=state["last_metrics"], covered=False,
                       caveats=[f"turn limit {MAX_TURNS}"])

    obs.record_agent_run(group=group, project=project, agent=cfg.name, model=cfg.model,
                         effort=cfg.effort, status="ok",
                         duration_ms=int((time.time() - t0) * 1000),
                         summary=final.answer[:200], input_tokens=tokens, output_tokens=0,
                         cache_read_tokens=0, cache_write_tokens=0)
    page = governed_page(pdir, final.metrics[0]) if final.metrics else ""
    return Result(question, final, rows=state["rows"], page=page, path="live",
                  tokens=tokens, turns=turns)


def ask(root: Path, group: str, project: str, question: str, *,
        direct: bool = False) -> Result:
    """The front door. Live when it can be, direct when it must. Always traced."""
    from pf import trace

    pdir = root / "groups" / group / "projects" / project
    with trace.start(root, "ask", question[:40], group=group, project=project) as tr:
        tr.event("question", question=question, direct=direct,
                 credentials=have_credentials())
        if direct or not have_credentials():
            res = answer_direct(pdir, question)
            tr.understanding(f"direct parse: metrics={res.answer.metrics} "
                             f"group_by={res.answer.group_by} where={res.answer.where!r}")
        else:
            res = answer_live(root, group, project, question)
        tr.event("answer", answer=res.answer.model_dump(), page=res.page, rows=len(res.rows),
                 path=res.path, tokens=res.tokens, turns=res.turns)
        return res
