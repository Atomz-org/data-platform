---
type: Vendor Upstream
title: Loop Engineering
description: 'loop governance: state, gate, budget, circuit breaker, autonomy ladder'
resource: https://github.com/cobusgreyling/loop-engineering
tags:
- vendor
- shape
- MIT
status: stable
sources:
- id: loop-engineering:LOOP.md
  resource: https://github.com/cobusgreyling/loop-engineering
  title: LOOP.md
- id: loop-engineering:STATE.md
  resource: https://github.com/cobusgreyling/loop-engineering
  title: STATE.md
- id: loop-engineering:gate.yaml
  resource: https://github.com/cobusgreyling/loop-engineering
  title: gate.yaml
- id: loop-engineering:loop-budget.md
  resource: https://github.com/cobusgreyling/loop-engineering
  title: loop-budget.md
- id: loop-engineering:loop-constraints.md
  resource: https://github.com/cobusgreyling/loop-engineering
  title: loop-constraints.md
- id: loop-engineering:patterns/registry.yaml
  resource: https://github.com/cobusgreyling/loop-engineering
  title: patterns/registry.yaml
- id: loop-engineering:patterns/registry.schema.json
  resource: https://github.com/cobusgreyling/loop-engineering
  title: patterns/registry.schema.json
- id: loop-engineering:docs/safety.md
  resource: https://github.com/cobusgreyling/loop-engineering
  title: docs/safety.md
- id: loop-engineering:skills/loop-verifier/SKILL.md
  resource: https://github.com/cobusgreyling/loop-engineering
  title: skills/loop-verifier/SKILL.md
- id: loop-engineering:patterns/dependency-sweeper.md
  resource: https://github.com/cobusgreyling/loop-engineering
  title: patterns/dependency-sweeper.md
- id: loop-engineering:patterns/pr-babysitter.md
  resource: https://github.com/cobusgreyling/loop-engineering
  title: patterns/pr-babysitter.md
---

# Loop Engineering

The governance shape for scheduled agent work: durable state, a path gate, a token budget, a circuit breaker and an autonomy ladder. The patterns are software-delivery loops; the subjects here are data-platform ones.

## Adopted

- **LOOP.md** (shape) -> LOOP.md
- **STATE.md** (shape) -> STATE.md
  Generated here, never hand-edited — a hand-edited state file stops being evidence.
- **gate.yaml** (shape) -> gate.yaml, gate.capabilities.yaml, platform/hooks/pre_tool_use.py
  Upstream's gate is advisory. Ours is a PreToolUse hook, so the denylist is structural rather than a rule an agent has to remember.
- **loop-budget.md** (shape) -> loop-budget.md, platform/src/pf/loops/runner.py
- **loop-constraints.md** (shape) -> loop-constraints.md
- **patterns/registry.yaml** (shape) -> platform/src/pf/loops/registry.py
  Same fields — autonomy level, cadence, token budget, human gates.
- **patterns/registry.schema.json** (parity) -> platform/src/pf/loops/registry.py
  Field parity, not instance validation. Our loops cannot satisfy the schema literally: `cadence` is a time grammar (`^[0-9]+[mhd]...`) and four of ours are event-driven (pre-commit, on manifest change, on dbt failure), while `file` requires a per-pattern markdown page where ours are one LOOP.md. So `pf vendor verify` asserts the weaker, honest property — every field upstream marks required has a counterpart in LoopSpec. If upstream adds a required governance concept, we are missing it, and that is the signal worth having.
- **docs/safety.md** (shape) -> platform/src/pf/loops/runner.py
  Circuit breaker — the same failure twice stops the loop rather than retrying it.
- **skills/loop-verifier/SKILL.md** (shape) -> platform/src/pf/loops/audit.py
- **patterns/dependency-sweeper.md** (shape) -> platform/src/pf/loops/registry.py, platform/src/pf/vendor/model.py
  The direct ancestor of the `vendor-drift` loop: report upstream movement, never apply it. L1 by construction — a submodule bump is a human decision.
- **patterns/pr-babysitter.md** (shape) -> .github/workflows/pr-report.yml, platform/src/pf/pr.py
  Ours reports rather than fixes. The PR comment carries blast radius, vendor drift and readiness; a human still merges.

## Declined

- **npx @cobusgreyling/loop-context tooling**
  The ledger, budget and circuit breaker are implemented in `pf` so they share the tracking DB with agent spend and impact history. One Node dependency in the critical path of every loop is not worth it.
- **patterns/issue-triage.md, patterns/ci-sweeper.md**
  Software-delivery subjects. Our loops watch freshness, drift, metric coverage and PII.
