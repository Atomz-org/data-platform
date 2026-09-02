"""The LLM call layer for loops.

Three things are centralised here because getting them wrong is expensive and
easy to miss:

  * **Cache prefix.** Rules + constraints + the project context card are
    byte-identical across every run of every loop, so they go in `system` behind
    one `cache_control` breakpoint with a 1h TTL. Cache reads bill at ~0.1x.
    Anything volatile (findings, timestamps, run ids) goes in the user turn,
    after the breakpoint. A `datetime.now()` in the system block would silently
    defeat the whole thing — verify with `cache_read_input_tokens`.
  * **Model and effort routing.** Mechanical work goes to Haiku; reasoning over
    lineage goes to Opus at medium. Paying Opus rates to reformat a list is the
    most common avoidable cost in an agentic platform. Routing declares *intent*
    here and `pf.agents.models` renders it into a request the target model
    actually accepts — `output_config.effort` is rejected outright by Haiku 4.5,
    so a naive cost-saving route to Haiku 400s on every call.
  * **Refusal handling.** `stop_reason == "refusal"` returns HTTP 200 with empty
    or partial content. Reading `content[0]` unconditionally breaks on it.
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from pf.agents.models import UnknownModel, cache_ttl, caches, request_params, spec

T = TypeVar("T", bound=BaseModel)

MAX_TOKENS = 16_000


class NoCredentials(RuntimeError):
    """Raised when no Anthropic credential is resolvable."""


@dataclass(frozen=True)
class AgentConfig:
    """Model routing for one step. See loop-budget.md for the rationale.

    `purpose` is not decoration — it is the reason the step is on this model, and
    it is what a reviewer checks when the bill moves. `cadence_minutes` picks the
    cache TTL: a 1h entry costs 2x to write and needs ~3 reads to pay for itself,
    so a step that runs less often than hourly must not ask for one.
    """

    name: str
    model: str
    purpose: str = ""
    effort: str = "medium"
    thinking: bool = True
    max_tokens: int = MAX_TOKENS
    cadence_minutes: int | None = None


# Routing table. Mirrors loop-budget.md — keep them in sync.
#
# The shape of the decision: judgement over lineage that a human would otherwise
# have to make goes to Opus; drafting against a known grammar goes to Sonnet;
# classifying rows that are already structured goes to Haiku. Every step returns
# a typed schema, so none of them pay for prose.
AGENTS = {
    "freshness_triage": AgentConfig(
        "freshness_triage", "claude-haiku-4-5",
        purpose="Classify already-structured monitor rows as signal or noise. "
                "Mechanical, highest cadence, no lineage reasoning — the cheapest "
                "model is correct here.",
        effort="low", thinking=False, cadence_minutes=120),
    "test_failure_triage": AgentConfig(
        "test_failure_triage", "claude-opus-5",
        purpose="Decide *why* a dbt node failed by reasoning over its lineage "
                "neighbourhood. A wrong root cause sends an engineer down the "
                "wrong path, so this is the one step worth Opus rates.",
        effort="medium", cadence_minutes=None),
    "metric_gap_proposer": AgentConfig(
        "metric_gap_proposer", "claude-sonnet-5",
        purpose="Draft MetricFlow definitions against a known grammar. Structured "
                "generation with a schema to check against — mid-tier is the "
                "quality/cost knee.",
        effort="low", cadence_minutes=1440),
    "fix_drafter": AgentConfig(
        "fix_drafter", "claude-sonnet-5",
        purpose="Rewrite one dbt file to implement a diagnosis that has already "
                "been made. The judgement was paid for at Opus rates upstream; "
                "this step is transcription against a file it is shown in full, "
                "checked by the gate, impact and Recce before anyone reads it.",
        effort="medium", cadence_minutes=None),
    "metric_answerer": AgentConfig(
        "metric_answerer", "claude-sonnet-5",
        purpose="Answer a business question using governed metrics only. Tool "
                "use over list/dimensions/query — never SQL — so the answer is "
                "a metric definition, not an opinion about a table.",
        effort="medium", thinking=False, cadence_minutes=60),
}


def validate_routing() -> list[str]:
    """Check every routed step against its model's real capabilities.

    Called by `pf models`. Catching an unsupported parameter here costs a unit
    test; catching it in production costs a 400 on a loop nobody is watching.
    """
    issues: list[str] = []
    for cfg in AGENTS.values():
        try:
            s = spec(cfg.model)
        except UnknownModel as exc:
            issues.append(f"{cfg.name}: {exc}")
            continue
        if cfg.effort and not s.supports_effort:
            issues.append(
                f"{cfg.name}: effort={cfg.effort!r} is dropped — {s.id} rejects "
                f"`output_config.effort`. Intent preserved, request still valid.")
        if cfg.max_tokens > s.max_output:
            issues.append(f"{cfg.name}: max_tokens {cfg.max_tokens} exceeds "
                          f"{s.id}'s {s.max_output} ceiling; it will be clamped.")
    return issues


# A client injected for tests and replays. `set_client(fake)` makes every
# agent path — loops, ask, evals — run end to end with no credential and no
# network, against whatever the fake returns. It is the only way to exercise
# a tool-use loop deterministically, and it is how the trace log is tested.
_CLIENT: dict[str, Any] = {"override": None}


def set_client(client: Any | None) -> None:
    _CLIENT["override"] = client


def have_credentials() -> bool:
    if _CLIENT["override"] is not None:
        return True
    return bool(os.environ.get("ANTHROPIC_API_KEY")
                or os.environ.get("ANTHROPIC_AUTH_TOKEN")
                or (Path.home() / ".config" / "anthropic" / "credentials").exists())


def client() -> Any:
    if _CLIENT["override"] is not None:
        return _CLIENT["override"]
    import anthropic

    if not have_credentials():
        raise NoCredentials(
            "no ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN or `ant auth login` profile. "
            "Loops fall back to their deterministic findings.")
    return anthropic.Anthropic()


def cached_prefix(root: Path, group: str, project: str,
                  cfg: AgentConfig | None = None) -> list[dict[str, Any]]:
    """The stable system prefix. Identical bytes across every run — that is the
    whole requirement for a cache hit.

    Two model-dependent details decide whether the marker does anything:

      * **The minimum cacheable prefix**, which is per model and not monotonic
        across generations (512 on Opus 5, 1024 on Sonnet 5, 4096 on Haiku 4.5).
        Below it the marker is silently ignored. This prefix is roughly a
        thousand tokens, so it caches on Opus, is marginal on Sonnet, and never
        caches on Haiku — we omit the marker there rather than implying it works.
      * **The TTL**, chosen from the step's cadence. Asking for 1h on a loop that
        runs every two hours pays the 2x write premium to read it zero times.
    """
    parts: list[str] = []
    for rel in ("platform/toolkits/ROUTING.md", "loop-constraints.md"):
        f = root / rel
        if f.exists():
            parts.append(f"<{Path(rel).stem}>\n{f.read_text(encoding='utf-8').strip()}\n</{Path(rel).stem}>")

    card = root / "groups" / group / "projects" / project / "kg" / "context_card.md"
    if card.exists():
        parts.append(f"<context_card>\n{_stable(card.read_text(encoding='utf-8'))}\n</context_card>")

    text = ("You are an agent operating inside a governed data platform.\n\n"
            + "\n\n".join(parts))
    block: dict[str, Any] = {"type": "text", "text": text}

    if cfg is None:
        return [block]

    # ~4 chars/token, the same local estimate `pf tokens` uses. Deliberately
    # conservative: over-estimating the prefix would put a marker on a request
    # that cannot cache, which reads as a working optimisation and is not one.
    approx_tokens = len(text) // 4
    if caches(cfg.model, approx_tokens):
        block["cache_control"] = {"type": "ephemeral",
                                  "ttl": cache_ttl(cfg.cadence_minutes)}
    return [block]


_DATE_RE = re.compile(r"\(generated \d{4}-\d{2}-\d{2}\)")


def _stable(text: str) -> str:
    """Strip the card's generation date.

    The card legitimately changes when the project changes — a new prefix is
    correct then. A date that ticks over daily with no content change is not:
    it invalidates the cache for every loop, every day, for nothing.
    """
    return _DATE_RE.sub("", text).strip()


# Tokens spent since the last reset. The loop runner reads this to enforce the
# per-run budget and to feed the daily circuit breaker.
_SPEND = {"tokens": 0}


def reset_spend() -> None:
    _SPEND["tokens"] = 0


def spend() -> int:
    return _SPEND["tokens"]


def call(
    cfg: AgentConfig,
    *,
    system: list[dict[str, Any]],
    user: str,
    output_format: type[T],
    group: str,
    project: str,
) -> tuple[T | None, dict[str, int]]:
    """One structured call. Returns (parsed, usage). Records the run either way.

    Structured output rather than prose: shorter, parseable by the caller, and
    no second round trip to reformat.
    """
    from pf import obs, trace

    tr = trace.get()
    tr.intent(cfg.purpose, agent=cfg.name, model=cfg.model, effort=cfg.effort)

    # Rendered per model: effort and thinking are dropped where the target model
    # rejects them, rather than 400-ing the loop.
    params = request_params(cfg.model, effort=cfg.effort, thinking=cfg.thinking,
                            max_tokens=cfg.max_tokens)
    tr.request(agent=cfg.name, model=cfg.model, params=params, system=system,
               user=user, schema=output_format.__name__)
    params |= {
        "system": system,
        "messages": [{"role": "user", "content": user}],
        # `messages.parse` is the documented structured-output path; it fills in
        # `output_config.format` from this schema. We pass `effort` in the same
        # `output_config` — re-check that the SDK merges rather than replaces it
        # on any anthropic upgrade, since a silent replace would drop effort
        # routing without failing.
        "output_format": output_format,
    }

    t0 = time.time()
    c = client()
    response = c.messages.parse(**params)
    elapsed = int((time.time() - t0) * 1000)

    u = response.usage
    usage = {
        "input_tokens": u.input_tokens,
        "output_tokens": u.output_tokens,
        "cache_read_tokens": getattr(u, "cache_read_input_tokens", 0) or 0,
        "cache_write_tokens": getattr(u, "cache_creation_input_tokens", 0) or 0,
    }

    # A refusal is HTTP 200 with empty or partial content — check before reading.
    refused = getattr(response, "stop_reason", None) == "refusal"
    parsed = None if refused else response.parsed_output

    _SPEND["tokens"] += usage["input_tokens"] + usage["output_tokens"]
    tr.response(agent=cfg.name, parsed=parsed, usage=usage,
                stop_reason=str(getattr(response, "stop_reason", "") or ""), ms=elapsed)

    obs.record_agent_run(
        group=group, project=project, agent=cfg.name, model=cfg.model,
        effort=cfg.effort, status="refusal" if refused else "ok",
        duration_ms=elapsed, summary=_summarise(parsed), **usage,
    )
    return parsed, usage


def _summarise(parsed: Any) -> str:
    if parsed is None:
        return "refused"
    for field in ("summary", "headline", "root_cause", "rationale"):
        v = getattr(parsed, field, None)
        if isinstance(v, str) and v:
            return v[:200]
    return type(parsed).__name__
