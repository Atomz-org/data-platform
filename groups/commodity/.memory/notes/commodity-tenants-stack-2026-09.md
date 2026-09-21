---
name: commodity-tenants-stack-2026-09
description: The commodity tenants work (india/us/rollup) is PR
type: project
status: resolved
---

On 2026-09-20 the commodity group became a family of markets: group seeds
(`commodities`, `markets`, `indicative_prices`), a `commodity_shared` Python
package, commodity-india conformed (`fct_landed_prices_daily`, `market_units`,
`import_duties`), new `commodity-us` and `commodity-rollup`. First pushed as
gh stack #474 (PRs #435–#473, one per ≤10-file commit); the user asked for a
single PR instead, so those were closed as superseded, their branches deleted,
and the same 39 commits now sit on branch `commodity-markets` as PR #475
(ready for review, base main). Each commit ≤10 files because the pre-commit gate (`gate.yaml`
maxFiles 12) blocks bigger ones and `--no-verify` is denied by the classifier.
Planner/executor: scratchpad `tenants/stack.py` (categorise → chunk → commit).
Safety snapshot branch `commodity-tenants/snapshot` can be deleted after merge.

**Why:** 39 PRs is a lot to keep straight; per-project CI is only green from
the last PR of each project (#447 India, #460 US, #472 roll-up) because a dbt
build needs seeds, staging and marts together.
**How to apply:** review/merge #475; the per-commit CI caveat no longer applies
(one PR, one CI run). A `commodity-tenants` branch name cannot be created while
any `commodity-tenants/*` ref exists — that is why the branch is `commodity-markets`. See [[pr-merge-classifier-limits]],
[[group-shared-python-by-path]].
