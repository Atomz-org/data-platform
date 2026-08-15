"""Context card rendering, and the bound that makes it safe at any project size.

The card is always-on context: every session pays for it on every request. What
keeps that affordable is that each section truncates, so a 1,000-model project
costs the same as a 10-model one. That property is easy to break by adding one
innocent-looking `", ".join(everything)`, and the project it breaks on is the
large one nobody wants to debug — so it is pinned here rather than assumed.
"""

from __future__ import annotations

import pytest
from pf.kg.card import (
    PROJECT_CARD_BUDGET,
    ROLLUP_KEYS,
    _bullets,
    _capped,
    _summarise,
    estimate_tokens,
)
from pf.kg.store import Node


def _models(n: int, *, tagged: bool = True, domains: int = 6) -> list[Node]:
    doms = [f"d{i}" for i in range(domains)]
    return [
        Node(id=str(i), kind="Model", layer="marts",
             name=f"fct_a_fairly_long_mart_model_name_{i}",
             label="A sentence describing what this mart contains.",
             props={"grain": "one row per customer per day",
                    "tags": [f"domain:{doms[i % domains]}", "criticality:high"]
                    if tagged else []})
        for i in range(n)
    ]


def _fmt(n: Node) -> str:
    return f"- `{n.name}` — grain: {n.props.get('grain')} — {n.label}"


# ------------------------------------------------------------------ bound ----
@pytest.mark.parametrize("count", [13, 100, 772, 5000])
def test_section_size_does_not_grow_with_the_project(count: int) -> None:
    """13 lines at 100 models and 13 at 5,000, or the always-on tier scales with
    the warehouse."""
    assert len(_bullets(_models(count), _fmt)) == 13


def test_a_huge_section_stays_far_inside_the_card_budget() -> None:
    rendered = "\n".join(_bullets(_models(5000), _fmt))
    assert estimate_tokens(rendered) < PROJECT_CARD_BUDGET // 3


def test_small_sections_are_listed_in_full() -> None:
    assert len(_bullets(_models(3), _fmt)) == 3


# ---------------------------------------------------------------- rollup ----
def test_the_remainder_is_described_not_just_counted() -> None:
    """"…and 760 more" is inside budget and tells a reader nothing about the
    project whose shape is the thing they needed."""
    tail = _bullets(_models(772), _fmt)[-1]
    assert "…and 760 more" in tail
    assert "by domain:" in tail
    assert "d0 (" in tail


def test_rollup_falls_back_cleanly_without_tags() -> None:
    tail = _bullets(_models(100, tagged=False), _fmt)[-1]
    assert "…and 88 more" in tail
    assert "by domain" not in tail


def test_a_single_group_is_not_a_grouping() -> None:
    """"by domain: finance (760)" says less than the count already did."""
    assert _summarise(_models(50, domains=1)) == ""


def test_rollup_prefers_the_most_useful_tag_namespace() -> None:
    assert ROLLUP_KEYS[0] == "domain"
    # criticality is present on every model, domain varies — domain wins.
    assert _summarise(_models(50)).startswith("by domain:")


def test_rollup_itself_is_bounded() -> None:
    """A project with 200 domains must not list 200 of them."""
    line = _summarise(_models(2000, domains=200))
    assert "+192 more" in line
    assert estimate_tokens(line) < 120


# ----------------------------------------------------------------- capped ----
def test_capped_reports_what_it_left_out() -> None:
    assert _capped(["a", "b", "c"], 2) == "a, b, +1 more"
    assert _capped(["a", "b"], 5) == "a, b"


def test_capped_says_none_rather_than_empty() -> None:
    assert _capped([], 5) == "none"


def test_capped_accepts_a_generator() -> None:
    assert _capped((str(i) for i in range(4)), 2) == "0, 1, +2 more"


def test_audit_and_card_agree_on_the_section_limit() -> None:
    """The audit tells people how many models the card will name. Two constants
    drifting apart makes that advice quietly wrong."""
    from pf.onboard.audit import _CARD_SECTION_LIMIT

    assert len(_bullets(_models(50), _fmt)) == _CARD_SECTION_LIMIT + 1
