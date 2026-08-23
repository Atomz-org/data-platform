"""The free tier: everything about the agent layer that can be checked without
spending a token.

These are not unit tests of helper functions. Each one pins an invariant whose
violation is invisible locally and expensive remotely — a request shape the
target model rejects, a cache marker that never hits, a prefix that changes on
every run. All of them are properties of the *platform*, so they hold identically
for every group and every project; only the last two read anything project-owned,
and then only its shape, never its content.

Outcomes are three-valued on purpose. `fail` is a defect. `warn` is a real
tension the platform has chosen to live with — surfacing it is useful, failing
CI over it is not.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pf.agents.base import AGENTS, cached_prefix
from pf.agents.models import UnknownModel, cache_ttl, caches, request_params, spec

Outcome = Literal["pass", "fail", "warn"]


@dataclass(frozen=True)
class ContractResult:
    name: str
    outcome: Outcome
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.outcome != "fail"


# Which agent each LLM-backed loop drives. Kept here rather than imported from
# the loop registry so a contract check never depends on the thing it checks.
LOOP_AGENTS = {
    "freshness-triage": "freshness_triage",
    "test-failure-triage": "test_failure_triage",
    "metric-gap-harvester": "metric_gap_proposer",
}


def _routed_models_have_specs(root: Path, group: str, project: str) -> ContractResult:
    """A step routed to a model with no capability spec cannot have its request
    rendered, so it fails at call time with a KeyError rather than a 400."""
    unknown = []
    for cfg in AGENTS.values():
        try:
            spec(cfg.model)
        except UnknownModel:
            unknown.append(f"{cfg.name} -> {cfg.model}")
    if unknown:
        return ContractResult("routed_models_have_specs", "fail",
                              "no spec for: " + ", ".join(unknown))
    return ContractResult("routed_models_have_specs", "pass",
                          f"{len(AGENTS)} routed steps")


def _requests_are_accepted_by_their_model(root: Path, group: str,
                                          project: str) -> ContractResult:
    """Render each step's real request and check it against the target's spec.

    The documented trap: `output_config.effort` is rejected outright by Haiku
    4.5, so the obvious cost saving — route the cheap mechanical step to Haiku,
    keep the `effort="low"` hint — 400s on every call. This is the check that
    catches that, and it is free.
    """
    problems: list[str] = []
    for cfg in AGENTS.values():
        s = spec(cfg.model)
        params = request_params(cfg.model, effort=cfg.effort, thinking=cfg.thinking,
                                max_tokens=cfg.max_tokens)

        if "output_config" in params and not s.supports_effort:
            problems.append(f"{cfg.name}: sends output_config to {s.id}, which rejects it")

        effort = params.get("output_config", {}).get("effort")
        if effort is not None and effort not in s.efforts:
            problems.append(f"{cfg.name}: effort={effort!r} not in {s.efforts}")

        if params["max_tokens"] > s.max_output:
            problems.append(
                f"{cfg.name}: max_tokens {params['max_tokens']} > {s.id} ceiling "
                f"{s.max_output}")

        thinking = params.get("thinking", {}).get("type")
        if thinking == "adaptive" and s.thinking != "adaptive":
            problems.append(f"{cfg.name}: adaptive thinking on {s.id}, which has none")
        if thinking == "enabled" and s.thinking != "budget":
            problems.append(f"{cfg.name}: budget thinking on {s.id}, which is adaptive")
        if thinking == "enabled" and params["thinking"]["budget_tokens"] >= params["max_tokens"]:
            problems.append(f"{cfg.name}: thinking budget is not below max_tokens")

    if problems:
        return ContractResult("requests_are_accepted_by_their_model", "fail",
                              "; ".join(problems))
    return ContractResult("requests_are_accepted_by_their_model", "pass",
                          f"{len(AGENTS)} requests render validly")


def _effort_intent_is_not_silently_lost(root: Path, group: str,
                                        project: str) -> ContractResult:
    """A step asking for an effort its model drops still runs — it just runs at
    the model's default. Worth knowing about; not worth failing over."""
    dropped = [f"{c.name} ({c.effort} -> {c.model} ignores it)"
               for c in AGENTS.values()
               if c.effort and not spec(c.model).supports_effort]
    if dropped:
        return ContractResult("effort_intent_is_not_silently_lost", "warn",
                              "; ".join(dropped))
    return ContractResult("effort_intent_is_not_silently_lost", "pass",
                          "every declared effort reaches its model")


def _cache_marker_only_where_it_caches(root: Path, group: str,
                                       project: str) -> ContractResult:
    """A `cache_control` marker below the model's minimum prefix is ignored
    silently — no error, no cache, and a routing table that looks optimised.

    Since the minimum is not monotonic across generations (512 on Opus 5, 4096
    on Haiku 4.5), this cannot be reasoned about from model tier alone.
    """
    problems, marked = [], []
    for cfg in AGENTS.values():
        blocks = cached_prefix(root, group, project, cfg)
        has_marker = any("cache_control" in b for b in blocks)
        approx = sum(len(b["text"]) for b in blocks) // 4
        will_cache = caches(cfg.model, approx)

        if has_marker and not will_cache:
            problems.append(
                f"{cfg.name}: marker on a {approx}-token prefix, but {cfg.model} "
                f"needs {spec(cfg.model).cache_min_tokens}")
        if has_marker:
            marked.append(f"{cfg.name}@{approx}t")

    if problems:
        return ContractResult("cache_marker_only_where_it_caches", "fail",
                              "; ".join(problems))
    return ContractResult(
        "cache_marker_only_where_it_caches", "pass",
        f"cached: {', '.join(marked) or 'none'}")


def _cache_ttl_matches_cadence(root: Path, group: str, project: str) -> ContractResult:
    """A 1h entry bills its write at 2x and needs ~3 reads to pay for itself. A
    loop slower than hourly never reads its own entry before it expires, so it
    pays the premium forever and hits zero times."""
    problems = []
    for cfg in AGENTS.values():
        ttl = cache_ttl(cfg.cadence_minutes)
        if ttl == "1h" and (cfg.cadence_minutes is None or cfg.cadence_minutes > 45):
            problems.append(f"{cfg.name}: 1h TTL on a {cfg.cadence_minutes}min cadence")
    if problems:
        return ContractResult("cache_ttl_matches_cadence", "fail", "; ".join(problems))
    return ContractResult("cache_ttl_matches_cadence", "pass",
                          "every TTL is justified by its cadence")


def _cached_prefix_is_byte_stable(root: Path, group: str, project: str) -> ContractResult:
    """Build the prefix twice and compare.

    The whole caching design rests on this one property, and the way it breaks
    is not a bug in the cache — it is someone adding a timestamp, a run id or a
    `datetime.now()` to the system block. That defeats every cache read on every
    loop and reports no error anywhere.
    """
    for cfg in AGENTS.values():
        first = cached_prefix(root, group, project, cfg)
        second = cached_prefix(root, group, project, cfg)
        if [b["text"] for b in first] != [b["text"] for b in second]:
            return ContractResult(
                "cached_prefix_is_byte_stable", "fail",
                f"{cfg.name}: prefix differs between two builds — something "
                f"volatile is in the system block")
    return ContractResult("cached_prefix_is_byte_stable", "pass",
                          "prefix is identical across builds")


def _card_regeneration_does_not_bust_the_cache(root: Path, group: str,
                                               project: str) -> ContractResult:
    """The context card carries a generation date. The card legitimately changes
    when the project changes — a new prefix is correct then. A date that ticks
    over daily with no content change is not: it would invalidate the prefix for
    every loop, every day, for nothing."""
    from pf.agents.base import _stable

    card = root / "groups" / group / "projects" / project / "kg" / "context_card.md"
    if not card.exists():
        return ContractResult("card_regeneration_does_not_bust_the_cache", "warn",
                              "no context card yet — run `pf kg card`")

    text = card.read_text(encoding="utf-8")
    today = _stable(text)
    # The same card, regenerated tomorrow with no content change.
    import re
    tomorrow = _stable(re.sub(r"\(generated \d{4}-\d{2}-\d{2}\)",
                              "(generated 2099-12-31)", text))
    if today != tomorrow:
        return ContractResult(
            "card_regeneration_does_not_bust_the_cache", "fail",
            "a date-only regeneration changes the prefix")
    return ContractResult("card_regeneration_does_not_bust_the_cache", "pass",
                          "date-only regeneration leaves the prefix untouched")


def _output_schemas_are_gradeable(root: Path, group: str, project: str) -> ContractResult:
    """Every field an eval can assert on must be either a closed set or
    documented.

    A free-text field with no `description` is a field the model is guessing the
    purpose of, and a field an eval can only assert weakly on. Closed `Literal`
    sets need no description — the options are the specification.
    """
    from typing import get_args, get_origin

    from pf.agents import loops as loop_agents
    from pf.evals.case import AGENT_INPUTS

    schemas = {
        "test_failure_triage": loop_agents.Diagnosis,
        "freshness_triage": loop_agents.AnomalyReport,
        "metric_gap_proposer": loop_agents.MetricProposals,
    }
    missing_schema = set(AGENT_INPUTS) - set(schemas)
    if missing_schema:
        return ContractResult("output_schemas_are_gradeable", "fail",
                              f"no output schema mapped for {sorted(missing_schema)}")

    undocumented: list[str] = []
    for agent, model in schemas.items():
        for field_name, info in model.model_fields.items():
            annotation = info.annotation
            is_literal = get_origin(annotation) is Literal and bool(get_args(annotation))
            if is_literal or _is_nested_model(annotation) or info.description:
                continue
            undocumented.append(f"{agent}.{field_name}")

    if undocumented:
        return ContractResult("output_schemas_are_gradeable", "warn",
                              "no description and not a closed set: "
                              + ", ".join(undocumented))
    return ContractResult("output_schemas_are_gradeable", "pass",
                          f"{len(schemas)} schemas fully specified")


def _is_nested_model(annotation: Any) -> bool:
    """A field carrying another schema, directly or in a collection.

    `list[MetricProposal]` needs no description of its own — the nested model's
    fields carry theirs, and it is those an eval actually asserts on.
    """
    from typing import get_args

    from pydantic import BaseModel

    def is_model(a: Any) -> bool:
        try:
            return issubclass(a, BaseModel)
        except TypeError:
            return False

    return is_model(annotation) or any(is_model(a) for a in get_args(annotation))


def _response_ceiling_fits_the_loop_budget(root: Path, group: str,
                                           project: str) -> ContractResult:
    """A single maximal response must not be able to blow the loop's per-run
    budget on its own.

    The runner compares tokens spent against `LoopSpec.token_budget` *after* the
    call, so an over-budget run is detected, not prevented. If `max_tokens`
    exceeds the budget, one verbose response trips the breaker and the loop
    reports failure having done nothing wrong.
    """
    from pf.loops.registry import SPECS

    tight = []
    for loop_name, agent_name in LOOP_AGENTS.items():
        cfg, loop = AGENTS.get(agent_name), SPECS.get(loop_name)
        if cfg is None or loop is None or not loop.token_budget:
            continue
        if cfg.max_tokens > loop.token_budget:
            tight.append(
                f"{loop_name}: {agent_name} may emit {cfg.max_tokens:,} tokens "
                f"against a {loop.token_budget:,} budget")
    if tight:
        return ContractResult("response_ceiling_fits_the_loop_budget", "warn",
                              "; ".join(tight))
    return ContractResult("response_ceiling_fits_the_loop_budget", "pass",
                          "no step can exceed its loop budget in one response")


def _toolkit_templates_are_loadable(root: Path, group: str,
                                    project: str) -> ContractResult:
    """Every template every toolkit ships must load and name a real agent.

    A malformed template is a platform defect with project-shaped consequences:
    `pf evals-gen` fails, or worse writes a broken case into someone's project,
    and the person who sees the error did not write the file.
    """
    from pf.evals.template import TemplateError, discover_templates

    try:
        templates = discover_templates(root)
    except TemplateError as exc:
        return ContractResult("toolkit_templates_are_loadable", "fail", str(exc))

    if not templates:
        return ContractResult("toolkit_templates_are_loadable", "warn",
                              "no toolkit ships eval templates")
    owners = sorted({t.toolkit for t in templates})
    return ContractResult("toolkit_templates_are_loadable", "pass",
                          f"{len(templates)} from {', '.join(owners)}")


def _toolkit_skills_declare_themselves(root: Path, group: str,
                                       project: str) -> ContractResult:
    """Each toolkit skill needs YAML frontmatter with a name and a description.

    This is what makes a skill discoverable. A skill missing it is invisible to
    the agent that needed it, and silently so — there is no error, the capability
    simply never gets used.
    """
    import yaml

    bad: list[str] = []
    count = 0
    for skill in sorted((root / "platform" / "toolkits").glob("*/skills/*/SKILL.md")):
        count += 1
        rel = f"{skill.parents[2].name}/{skill.parent.name}"
        text = skill.read_text(encoding="utf-8")
        if not text.startswith("---"):
            bad.append(f"{rel}: no frontmatter")
            continue
        _, _, rest = text.partition("---")
        block, _, _ = rest.partition("---")
        try:
            meta = yaml.safe_load(block) or {}
        except yaml.YAMLError as exc:
            bad.append(f"{rel}: unparseable frontmatter ({exc.__class__.__name__})")
            continue
        missing = [k for k in ("name", "description") if not meta.get(k)]
        if missing:
            bad.append(f"{rel}: missing {', '.join(missing)}")

    if bad:
        return ContractResult("toolkit_skills_declare_themselves", "fail",
                              "; ".join(bad[:5]))
    return ContractResult("toolkit_skills_declare_themselves", "pass",
                          f"{count} skills declare name and description")


CONTRACT_CHECKS: tuple[Callable[[Path, str, str], ContractResult], ...] = (
    _routed_models_have_specs,
    _requests_are_accepted_by_their_model,
    _effort_intent_is_not_silently_lost,
    _cache_marker_only_where_it_caches,
    _cache_ttl_matches_cadence,
    _cached_prefix_is_byte_stable,
    _card_regeneration_does_not_bust_the_cache,
    _output_schemas_are_gradeable,
    _response_ceiling_fits_the_loop_budget,
    _toolkit_templates_are_loadable,
    _toolkit_skills_declare_themselves,
)


def run_contract(root: Path, group: str, project: str) -> list[ContractResult]:
    """Run every contract check. Never calls a model; never needs a credential."""
    return [check(root, group, project) for check in CONTRACT_CHECKS]
