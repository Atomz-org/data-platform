---
name: root-claude-md-token-budget
description: root CLAUDE.md is hard-capped at 700 tokens (ROUTER_BUDGET, pf/kg/card.py) and CI-enforced by `pf tokens`; it was already at 698/700 before any edit
type: project
status: active
---

The repo root `CLAUDE.md` is not an ordinary docs file — it is `ROUTER_BUDGET
= 700` in `platform/src/pf/kg/card.py`, "loaded by every session," and `pf
tokens` fails the build (`platform.yml` → `converged`) when it goes over.
Estimate is `len(text) // 4` (`estimate_tokens`, same file), so ~2800 chars is
the real ceiling. The committed version on main measured 698/700 — two tokens
of headroom, by design, not by accident.

**Why:** on 2026-09-21 I expanded it from 50 to 174 lines (commands, a
generated-files table, a verification-trap section, the commit gate) after
`/init`. It measured 2109/700 — three times over — and `pf tokens` went from
OK to a hard CI failure I introduced myself, on a file I hadn't re-measured
after editing.

**How to apply:** never add prose to the root `CLAUDE.md` without running `uv
run pf tokens` immediately after and checking the `platform / CLAUDE.md` row.
Anything beyond a one-line pointer belongs in a separate `docs/*.md` page
instead — README.md and other docs pages carry no such budget. Recovered by
reverting to the original content (only fixing a stale vendor count,
twenty-two → twenty-three) and moving all new material to the new
`docs/DEVELOPMENT.md`, referenced from `README.md`. Same rule applies to
`PROJECT_CLAUDE_BUDGET` (600) and `GROUP_CLAUDE_BUDGET` (400) for any
group/project-level `CLAUDE.md`. Related: [[arch-gate-verification-trap]].
