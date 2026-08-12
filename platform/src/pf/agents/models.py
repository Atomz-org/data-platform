"""Model capability registry — what each model actually accepts.

Routing a step to a model is two decisions, and only one of them is taste. The
taste part is "which model is worth its price for this step". The other part is
mechanical: each model accepts a *different request shape*, and sending the wrong
one is a 400, not a degradation.

That second part is what this module owns. `AgentConfig` declares intent
(`effort="low"`, `thinking=False`); `request_params()` renders it into a payload
the target model will actually accept, dropping what that model does not support.

The facts below come from the Anthropic API docs, not from inference:

  * `output_config.effort` is **rejected on Haiku 4.5** (and Sonnet 4.5). It is
    accepted on Opus 5 / Sonnet 5 across low..max. Routing a cheap mechanical
    step to Haiku *with an effort hint* — exactly what a cost-conscious routing
    table wants to do — therefore fails every call.
  * Adaptive thinking (`{"type": "adaptive"}`) is the only thinking mode on
    Opus 5 / Sonnet 5, and is **on by default** on both. Haiku 4.5 predates it
    and takes `{"type": "enabled", "budget_tokens": N}` instead.
  * Prompt caching has a per-model **minimum cacheable prefix**. It is not
    monotonic across generations: 512 on Opus 5, 1024 on Sonnet 5, 4096 on
    Haiku 4.5. Below the minimum a `cache_control` marker is silently ignored —
    no error, just no cache. A shared prefix that caches on Opus can therefore
    never cache on Haiku.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

Effort = Literal["low", "medium", "high", "xhigh", "max"]
ThinkingMode = Literal["adaptive", "budget", "none"]


@dataclass(frozen=True)
class ModelSpec:
    """What one model accepts, and what it costs."""

    id: str
    thinking: ThinkingMode
    thinking_on_by_default: bool
    supports_effort: bool
    efforts: tuple[str, ...]
    cache_min_tokens: int
    max_output: int
    usd_in: float             # per million input tokens
    usd_out: float            # per million output tokens
    structured_outputs: bool = True

    def clamp_effort(self, effort: str) -> str | None:
        """The nearest effort this model accepts, or None if it accepts none."""
        if not self.supports_effort:
            return None
        return effort if effort in self.efforts else self.efforts[-1]


# Only models this platform actually routes to. Adding one here is the single
# edit needed to make it available to every agent — see `pf models`.
MODELS: dict[str, ModelSpec] = {
    "claude-opus-5": ModelSpec(
        id="claude-opus-5", thinking="adaptive", thinking_on_by_default=True,
        supports_effort=True, efforts=("low", "medium", "high", "xhigh", "max"),
        cache_min_tokens=512, max_output=128_000, usd_in=5.00, usd_out=25.00,
    ),
    "claude-sonnet-5": ModelSpec(
        id="claude-sonnet-5", thinking="adaptive", thinking_on_by_default=True,
        supports_effort=True, efforts=("low", "medium", "high", "xhigh", "max"),
        cache_min_tokens=1024, max_output=128_000, usd_in=3.00, usd_out=15.00,
    ),
    # No effort parameter, no adaptive thinking, and a 4096-token cache floor
    # that a compact context card will not reach. Route mechanical, high-cadence
    # work here and expect an uncached prefix.
    "claude-haiku-4-5": ModelSpec(
        id="claude-haiku-4-5", thinking="budget", thinking_on_by_default=False,
        supports_effort=False, efforts=(),
        cache_min_tokens=4096, max_output=64_000, usd_in=1.00, usd_out=5.00,
    ),
}


class UnknownModel(KeyError):
    """Raised when an agent routes to a model this platform has no spec for."""


def spec(model: str) -> ModelSpec:
    if model not in MODELS:
        raise UnknownModel(
            f"no capability spec for '{model}'. Add it to pf.agents.models.MODELS "
            f"— routing to a model whose request shape is unknown is how you get a "
            f"400 in production. Known: {', '.join(sorted(MODELS))}")
    return MODELS[model]


def request_params(
    model: str,
    *,
    effort: str = "medium",
    thinking: bool = True,
    max_tokens: int = 16_000,
    budget_tokens: int = 4_000,
) -> dict[str, Any]:
    """Render intent into a payload the target model accepts.

    Everything this drops, it drops because the target model rejects it — never
    to save tokens. Cost control is the routing decision, not a silent downgrade
    of the request.
    """
    s = spec(model)
    params: dict[str, Any] = {"model": s.id, "max_tokens": min(max_tokens, s.max_output)}

    resolved = s.clamp_effort(effort)
    if resolved is not None:
        params["output_config"] = {"effort": resolved}

    match (s.thinking, thinking):
        case ("adaptive", True):
            params["thinking"] = {"type": "adaptive"}
        case ("adaptive", False):
            # Accepted only at effort `high` or below on Opus 5; above that it is
            # a 400. Cheaper and safer to leave adaptive thinking on and let a low
            # effort do the cost control.
            if resolved in (None, "low", "medium", "high"):
                params["thinking"] = {"type": "disabled"}
        case ("budget", True):
            params["thinking"] = {"type": "enabled",
                                  "budget_tokens": min(budget_tokens, params["max_tokens"] - 1)}
        case _:
            pass  # thinking off on a model that has no adaptive mode: send nothing

    return params


def caches(model: str, prefix_tokens: int) -> bool:
    """Whether a prefix of this size will actually cache on this model."""
    return prefix_tokens >= spec(model).cache_min_tokens


def cache_ttl(cadence_minutes: int | None) -> str:
    """Pick a cache TTL from how often the caller runs.

    A 1h TTL bills the write at 2x (vs 1.25x for 5m) and needs ~3 reads to pay
    for itself. A loop on a 2h cadence never reads its own entry — the TTL
    expires first — so it would pay the premium forever and hit zero times.
    """
    if cadence_minutes is not None and cadence_minutes <= 45:
        return "1h"
    return "5m"


def estimate_usd(model: str, input_tokens: int, output_tokens: int,
                 cache_read: int = 0, cache_write: int = 0, ttl: str = "5m") -> float:
    """Cost of one call, with cache reads at 0.1x and writes at 1.25x/2x."""
    s = spec(model)
    write_multiplier = 2.0 if ttl == "1h" else 1.25
    return round(
        (input_tokens * s.usd_in
         + output_tokens * s.usd_out
         + cache_read * s.usd_in * 0.1
         + cache_write * s.usd_in * write_multiplier) / 1_000_000,
        6,
    )
