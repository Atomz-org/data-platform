---
name: jaffle-shop-context-card-over-budget
description: jaffle-shop's committed kg/context_card.md is 1585/1500 tokens on main right now; pf tokens never catches it because platform.yml only triggers on platform/** paths
type: project
status: active
agent: claude-code
---

`uv run pf tokens` reports `jaffle/jaffle-shop context_card 1585/1500 OVER` on
main as of 2026-09-21, unmodified and pre-existing (not something a session
introduced — `git status` on the file is clean). jaffle-shop is the largest
project by far (57 tables, 1088 models per `docs/ARCHITECTURE.md`), so this is
plausibly the card legitimately outgrowing its budget rather than a generator
bug.

**Why nothing caught it:** `pf tokens` only runs in `.github/workflows/platform.yml`
(the `converged` job), which triggers on `pull_request` only when the diff
touches `platform/**`, `pyproject.toml`, `uv.lock`, `gate.yaml`,
`groups/*/group.yaml`, or its own workflow file — never on an ordinary
`groups/<g>/projects/<p>/**` change, and never on a push to `main`. A card can
cross its budget and nothing built ever says so.

**How to apply:** this needs a human call (trim the card's content, or raise
`PROJECT_CARD_BUDGET` for large projects) — not an agent fix. If asked to "fix
CI" or "update docs" again, don't assume `pf tokens` passing locally means
anything: check it explicitly, since the trigger gap means it can be broken on
main indefinitely without any red run anywhere. Related:
[[root-claude-md-token-budget]].
