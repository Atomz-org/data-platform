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
    most common avoidable cost in an agentic platform.
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

T = TypeVar("T", bound=BaseModel)

MAX_TOKENS = 16_000


class NoCredentials(RuntimeError):
    """Raised when no Anthropic credential is resolvable."""


@dataclass(frozen=True)
class AgentConfig:
    """Model routing for one agent. See loop-budget.md for the rationale."""

    name: str
    model: str
    effort: str = "medium"
    thinking: bool = True
    max_tokens: int = MAX_TOKENS


# Routing table. Mirrors loop-budget.md — keep them in sync.
AGENTS = {
    "freshness_triage": AgentConfig("freshness_triage", "claude-haiku-4-5",
                                    effort="low", thinking=False),
    "test_failure_triage": AgentConfig("test_failure_triage", "claude-opus-5",
                                       effort="medium"),
    "metric_gap_proposer": AgentConfig("metric_gap_proposer", "claude-sonnet-5",
                                       effort="low"),
}


def have_credentials() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY")
                or os.environ.get("ANTHROPIC_AUTH_TOKEN")
                or (Path.home() / ".config" / "anthropic" / "credentials").exists())


def client() -> Any:
    import anthropic

    if not have_credentials():
        raise NoCredentials(
            "no ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN or `ant auth login` profile. "
            "Loops fall back to their deterministic findings.")
    return anthropic.Anthropic()


def cached_prefix(root: Path, group: str, project: str) -> list[dict[str, Any]]:
    """The stable system prefix. Identical bytes across every run — that is the
    whole requirement for a cache hit."""
    parts: list[str] = []
    for rel in ("platform/toolkits/ROUTING.md", "loop-constraints.md"):
        f = root / rel
        if f.exists():
            parts.append(f"<{Path(rel).stem}>\n{f.read_text().strip()}\n</{Path(rel).stem}>")

    card = root / "groups" / group / "projects" / project / "kg" / "context_card.md"
    if card.exists():
        parts.append(f"<context_card>\n{_stable(card.read_text())}\n</context_card>")

    text = ("You are an agent operating inside a governed data platform.\n\n"
            + "\n\n".join(parts))
    # One breakpoint at the end of the stable prefix. 1h TTL because loops run
    # on cadences measured in hours, not seconds.
    return [{"type": "text", "text": text,
             "cache_control": {"type": "ephemeral", "ttl": "1h"}}]


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
    from pf import obs

    params: dict[str, Any] = {
        "model": cfg.model,
        "max_tokens": cfg.max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
        "output_format": output_format,
        "output_config": {"effort": cfg.effort},
    }
    if cfg.thinking:
        params["thinking"] = {"type": "adaptive"}

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
