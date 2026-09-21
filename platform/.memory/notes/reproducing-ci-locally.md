---
name: reproducing-ci-locally
description: Two traps that make a local "CI passes" result wrong in this repo — a stale .venv and a submodule-less clone
type: project
status: active
---

Reproducing a data-platform CI job locally needs two things that are easy to
miss, both of which produced a confident false "passes" on 2026-09-20 and cost
CI rounds on PR #415.

**1. `uv sync --frozen` first.** The repo `.venv` drifts from `uv.lock`. CI runs
`uv sync`, so a stale venv means a different dbt and different parse output —
which changes generated artefacts like `kg/architecture.md`. `uv run` does not
reliably re-sync it.

**2. `git clone --shared` has no submodules.** Convenient and fast for
reproducing the `converged` job, but anything reading `vendor/**` silently
reports the wrong answer. `pf vendor card` computed every upstream as `ok`
locally and `drift` on the runner, and `docs/VENDOR-CARD.md` was the last file
failing the gate after everything else converged. Fetch the pins, or take the
runner's own diff from the failing job's log.

Also: the same commit renders `kg/architecture.md` differently in the
`converged` job (bootstraps, never builds) and the per-project `architecture`
job (builds, never bootstraps) — three rows differ, so a committed map can only
satisfy one. Commit the `pf kg build` + `pf arch` render; that is the one a job
actually checks.

**3. A stale `transform/target/manifest.json` (found 2026-09-21).** `pf kg
build` reads dbt models, columns, tests and exposures from this file, and
`ensure_manifest` (`pf.runtime.dbt_runtime`) only reparses when it is *absent*
or `dbt_packages/` is missing a declared package — never because a model or
`_reporting__exposures.yml` file changed underneath it. `target/` is
gitignored, so a checkout can carry a manifest from days earlier. Symptom: `pf
kg build` then `pf arch <g> <p> --check` still fails, with the diff going the
*wrong direction* — counts the check wants to raise (new exposures, new tests)
instead render as if they should be lowered, because the stale manifest
predates the model change entirely. This is not the same failure as "no
manifest" (which degrades visibly) — it degrades *confidently*, using real but
outdated dbt state. Fix: `rm transform/target/manifest.json` before `pf kg
build`, not just `uv sync --frozen`. Caught on acme-eu/acme-us/jaffle-shop
after PR #477 merged — all three "failures" were a local artefact, not a real
regression; the committed maps were already correct.

Related: [[open-pr-stacks-2026-09]], [[uv-workspace-hook-deadlock]],
[[arch-gate-verification-trap]]
