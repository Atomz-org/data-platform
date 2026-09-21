---
name: test-index-budget-exhausted
description: platform/tests/README.md is 1596/1600 tokens; a 55th test file fails the budget and the sanctioned fix is the per-group rollup in testmap.render_index, never a bigger number
type: project
status: active
agent: claude-code
---

**Why:** `test_the_index_is_small_enough_to_be_worth_reading` caps
`platform/tests/README.md` at 1600 tokens, and its comment is explicit that
the budget already grew once (1200 → 1600) and that "a per-group rollup is the
answer the next time it binds". It has now bound twice. The first time, the
row format changed from a table to a list (~110 tokens). The second time, the
code-graph wiring tests were folded into `test_agent_context.py` instead of
getting their own file, which was the cohesive choice anyway — the check they
exercise is one call — but it also bought only a few tokens.

**How to apply:** at 1596/1600 there is room for no new test *file* at all; a
55th file is roughly 25 tokens and fails the build. Do not raise the number,
and do not shave docstrings to fit: the first line of each test file's
docstring is what the index shows, so trimming it degrades the artefact the
budget exists to protect. Implement the rollup in `pf.testmap.render_index` —
per directory, the heading and counts it already prints, with the file links
and the per-file subjects dropped or summarised. `pf test where <term>` is how
a subject is found on demand once that lands, which is the same
"queried, never loaded" trade the context cards already make.
