# CI/CD — the three platform jobs, and the record they leave

**Written for:** an engineer who has just seen a red check and wants to know
what it was actually measuring.

[`docs/CI.md`](../CI.md) is the map of all twenty-three workflows and which
paths wake them. This folder is the opposite: three jobs, in depth, with the
exact condition that turns each one red.

| Page | What it answers |
|---|---|
| [gates.md](gates.md) | Four commands that ask whether the shared platform still holds together |
| [converged.md](converged.md) | Is what is checked in still what the generator produces? |
| [tests.md](tests.md) | Does the shared code still work, and is every index that describes it current? |
| [audit-trail.md](audit-trail.md) | How this replaces a hand-written `.compliance-trace/` folder — and where it currently falls short |

---

## The one sentence version

**`tests` runs the code. `gates` asks whether the platform still holds
together. `converged` asks whether the generated files are stale.**

Almost every job is one `pf` command with the same name as the check, so a red
check is reproducible on your laptop. That is deliberate: a gate you cannot
reproduce locally is a gate people learn to re-run until it passes.

## The shape of nearly every failure

Once you have read all three, the same pattern appears in most red checks, and
it is rarely a bug in your code:

> **Something in this repo is generated from something else, and you changed
> the source without regenerating the projection.**

An index of the test suite. A map of the architecture. A card describing the
vendored upstreams. The onboarding guide. Each is derived, each is committed,
and CI re-derives it and compares byte for byte.

The fix is almost always one command, and the failure message names it:

```bash
uv run pf test index      # platform/tests/README.md
uv run pf arch build      # docs/ARCHITECTURE.md
uv run pf memory index    # .memory/MEMORY.md
uv run pf vendor docs     # docs/VENDOR-CARD.md, docs/VENDOR.md
uv run pf context refresh # several of the above at once
uv run pf bootstrap --all # every generated file, all 11 projects
```

## Why generate-and-compare at all

A document that describes the code is a promise. Left to a human it drifts,
quietly, and the day it matters it is wrong. Generating it from the code and
failing the build on a difference makes the promise mechanical: the map cannot
lie about the territory, because the map is built from the territory on every
pull request.

That is the same idea as the audit trail in [audit-trail.md](audit-trail.md) —
derive, never assert.

## Honest notes

These are the things reading the implementation turned up that the YAML does
not advertise. Each one is verified against the source.

- **`tests` and `suite` run the identical command.** `platform.yml:54` and
  `platform-tests.yml:101-102` both run `uv run pytest platform/tests -q`.
  Two checks, one suite, on two different path filters.
- **Several steps cannot fail.** Every "Vendored upstreams" step swallows each
  failure into a `::warning` and exits 0. An unreachable pin means 33+ tests
  silently skip rather than a red build.
- **`converged` does not watch `vendor/**`.** Its path filter
  (`platform.yml:12-18`) never lists it, so a commit that only moves submodule
  pins does not trigger the job that would have caught the stale vendor card.
  See [converged.md](converged.md).
- **Two provenance steps cannot fail on CI as configured.** See
  [audit-trail.md](audit-trail.md); this is the most important one here.
