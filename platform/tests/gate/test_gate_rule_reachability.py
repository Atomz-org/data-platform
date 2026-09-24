"""Every rule in `gate.yaml` is proved to still bite — or declared not to.

The existing gate tests pin the cases someone thought of. This file pins the
ones nobody did: it reads the policy itself and asks, of every pattern in it,
whether that pattern still claims anything.

A rule that matches nothing is indistinguishable from a repository with no
violations, and it fails silently and permanently. Both bugs of that shape this
repo has already hit are recorded in `pf/loops/gate.py`: `lstrip` stripping the
dot off `.env` so a denylisted secret became writable, and `in_project`
resolved from the target path so `platform_denylist` was unreachable. Neither
was a wrong rule; both were live rules that quietly stopped matching, and a
hand-written suite cannot catch the next one because the next one will be in a
pattern nobody wrote a case for.

Shadowing is not itself a bug here — the policy deliberately lists 17 generated
artefacts in both `denylist` and `denylist_except` (the denylist says "not by
hand", the exception says "git may carry it"). What these tests refuse is an
*undeclared* shadow: a rule neutralised by a pattern that was never written to
neutralise it. That is the `.env.example` bug in general form.
"""

from __future__ import annotations

import pytest
from conftest import REPO_ROOT
from pf.loops.gate import check_path, load_policy

POLICY = load_policy(REPO_ROOT)

#: `impact_required` entries that `autoMergeAllowlist` currently outranks, so
#: the blast-radius warning never fires for them. `check_path` consults the
#: allowlist before `impact_required`, and the allowlist carries a blanket
#: `**/*.sql`, so every dbt model in the repo resolves to `allow` — which is
#: also the branch `platform/hooks/pre_tool_use.py` needs in order to print the
#: blast radius at all.
#:
#: Frozen deliberately rather than fixed here: whether the allowlist should
#: stop covering `**/*.sql`, or `impact_required` should be consulted first, is
#: a policy decision and not a test's to make. What the freeze buys is that a
#: *new* impact rule cannot silently join this list.
KNOWN_UNREACHABLE_IMPACT_RULES = frozenset({
    "**/transform/models/**/*.sql",
    "**/transform/macros/**/*.sql",
})


def _path_matching(pattern: str) -> str:
    """A concrete path built from the pattern, so it matches by construction.

    The point is not to guess what the author meant — it is to hold up a path
    the rule must claim. If a rule does not claim even this one, it claims
    nothing at all.
    """
    p = pattern.replace("**/", "seg/").replace("/**", "/seg").replace("**", "seg")
    return p.replace("*", "x")


def _patterns(key: str) -> list[str]:
    return [p for p in (POLICY.get(key) or []) if isinstance(p, str)]


@pytest.mark.parametrize("pattern", _patterns("denylist"))
def test_a_denylist_pattern_denies_or_is_declared_as_an_exception(pattern: str) -> None:
    """A denylist entry either bites, or says in `denylist_except` that it does not.

    The failure this catches is an exception pattern that over-matches and
    neutralises a protection nobody meant it to reach.
    """
    path = _path_matching(pattern)
    result = check_path(path, REPO_ROOT)
    if result.verdict == "deny":
        return
    assert pattern in set(_patterns("denylist_except")), (
        f"denylist pattern {pattern!r} claims nothing — {path!r} came back "
        f"{result.verdict!r} via rule {result.rule!r} — and it is not listed in "
        "denylist_except. Some exception pattern is over-matching and silently "
        "removing a protection. Either narrow that exception, or list this "
        "pattern in denylist_except so the hole is a decision rather than an accident."
    )


@pytest.mark.parametrize("pattern", _patterns("platform_denylist"))
def test_every_platform_denylist_pattern_fires_in_a_project_session(pattern: str) -> None:
    """These apply only inside a project session — the bug that once hid all of them."""
    path = _path_matching(pattern)
    result = check_path(path, REPO_ROOT, in_project=True)
    assert result.verdict == "deny", (
        f"platform_denylist pattern {pattern!r} claims nothing from a project "
        f"session: {path!r} came back {result.verdict!r} via {result.rule!r}."
    )


@pytest.mark.parametrize("pattern", _patterns("platform_denylist"))
def test_platform_denylist_stays_silent_outside_a_project(pattern: str) -> None:
    """The other direction: platform work is editable from a platform session."""
    path = _path_matching(pattern)
    result = check_path(path, REPO_ROOT, in_project=False)
    assert not result.rule.startswith("platform_denylist:"), (
        f"{path!r} was refused by {result.rule!r} outside a project session; "
        "shared infra is editable from a platform session by design."
    )


@pytest.mark.parametrize("pattern", _patterns("impact_required"))
def test_an_impact_rule_warns_or_is_a_known_dead_rule(pattern: str) -> None:
    """A blast radius that is never demanded is the failure this rule exists to prevent."""
    path = _path_matching(pattern)
    result = check_path(path, REPO_ROOT)
    if result.verdict in {"warn", "deny"}:
        return
    assert pattern in KNOWN_UNREACHABLE_IMPACT_RULES, (
        f"impact_required pattern {pattern!r} is born dead: {path!r} came back "
        f"{result.verdict!r} via {result.rule!r}, so no blast radius is ever "
        "demanded for it and pre_tool_use.py never reaches its warn branch. "
        "Fix the precedence, or add it to KNOWN_UNREACHABLE_IMPACT_RULES with "
        "a reason."
    )


def test_the_known_dead_impact_rules_are_still_in_the_policy() -> None:
    """Retire the freeze when the rule it excuses is gone, so it cannot rot."""
    declared = set(_patterns("impact_required"))
    stale = KNOWN_UNREACHABLE_IMPACT_RULES - declared
    assert not stale, (
        f"KNOWN_UNREACHABLE_IMPACT_RULES names {sorted(stale)}, which gate.yaml "
        "no longer declares. Drop them from the freeze."
    )


@pytest.mark.parametrize("pattern", _patterns("denylist_except"))
def test_every_exception_still_exempts_something(pattern: str) -> None:
    """An exception that exempts nothing is dead weight that reads as a promise."""
    path = _path_matching(pattern)
    result = check_path(path, REPO_ROOT)
    assert result.rule == "denylist_except", (
        f"denylist_except pattern {pattern!r} exempts nothing: {path!r} came "
        f"back via {result.rule!r}."
    )


def test_the_policy_actually_loaded() -> None:
    """Guard the guard: an empty policy would make every case above vacuous."""
    assert _patterns("denylist"), "no denylist patterns loaded from gate.yaml"
    assert _patterns("platform_denylist"), "no platform_denylist patterns loaded"
    assert _patterns("impact_required"), "no impact_required patterns loaded"
