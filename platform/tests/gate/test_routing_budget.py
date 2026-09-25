"""The ROUTING.md token budget is one named policy, stated once.

ROUTING.md is the toolkit precedence ladder. Every session loads it, and every
LLM-backed loop puts it in its byte-stable system prefix, so a line added there
is paid on every request in the repository. That is why it is budgeted.

It was the only always-on artefact whose budget was a bare `400` inside
`pf tokens`, written twice on one line and copied by hand into two docs tables.
Moving it meant finding every copy, and a copy missed would keep telling
readers the old limit. These tests make the budget a single named constant
beside the others in `pf.kg.card`, enforced from there, and stated identically
wherever the docs quote it.
"""

from __future__ import annotations

import re

from conftest import REPO_ROOT

ROUTING = REPO_ROOT / "platform" / "toolkits" / "ROUTING.md"


def test_the_budget_is_a_named_constant_beside_the_others() -> None:
    from pf.kg import card

    assert isinstance(card.ROUTING_BUDGET, int)
    # A ceiling, not a target: never below what the always-on router allows
    # for itself, which would be a silent tightening rather than a policy.
    assert 0 < card.ROUTING_BUDGET <= card.ROUTER_BUDGET


def test_pf_tokens_enforces_the_constant_and_no_literal() -> None:
    source = (REPO_ROOT / "platform" / "src" / "pf" / "cli.py").read_text(encoding="utf-8")
    line = next(ln for ln in source.splitlines() if '"ROUTING.md"' in ln and "rows.append" in ln)
    assert "ROUTING_BUDGET" in line, "pf tokens reports ROUTING.md against something other than the constant"
    assert not re.search(r"\b\d{3,}\b", line), f"a literal budget is back in pf tokens: {line.strip()}"


def test_the_committed_ladder_is_within_budget() -> None:
    from pf.kg.card import ROUTING_BUDGET, estimate_tokens

    n = estimate_tokens(ROUTING.read_text(encoding="utf-8"))
    assert n <= ROUTING_BUDGET, (
        f"ROUTING.md is ~{n} tokens against {ROUTING_BUDGET}. Shorten a rule, or "
        "raise pf.kg.card.ROUTING_BUDGET in a pull request that says why"
    )


def test_every_doc_that_quotes_the_budget_quotes_the_constant() -> None:
    from pf.kg.card import ROUTING_BUDGET

    quoted = {
        "README.md": r"^\| ROUTING\.md \| (\d+) \|",
        "docs/ENGINEERING.md": r"^\| platform \| `platform/toolkits/ROUTING\.md` \|.*\| (\d+) \|$",
    }
    for rel, pattern in quoted.items():
        found = re.findall(pattern, (REPO_ROOT / rel).read_text(encoding="utf-8"), re.M)
        assert found, f"{rel} no longer quotes the ROUTING.md budget; update this test"
        assert {int(n) for n in found} == {ROUTING_BUDGET}, f"{rel} states {found}, the policy is {ROUTING_BUDGET}"
