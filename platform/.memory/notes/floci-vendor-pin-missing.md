---
name: floci-vendor-pin-missing
description: registry.yaml has a full floci entry (adoptions, declines, why) but .gitmodules never got a vendor/floci submodule — pf vendor verify reports it missing
type: project
status: active
agent: claude-code
---

`platform/src/pf/vendor/registry.yaml` (id `floci`, ~line 946) documents an S3
emulator adopted for `pf.artifacts` testing — a compose file
(`platform/deploy/compose.floci.yaml`), adopted/declined paths, full `why:`
reasoning. But `.gitmodules` has never had a `vendor/floci` submodule entry —
`git log -S'vendor/floci' -- .gitmodules` is empty across the repository's
whole history. `pf vendor list` and `pf vendor verify` both correctly report
it `missing`; this is why the registry currently totals 24 upstreams while
only 23 are actually pinned submodules.

**Why it matters:** it inflates `pf vendor list`'s adoption/decline counts
(88/51) with a pin that was never fetchable, and any future doc or generator
that trusts the registry's total (24) instead of `.gitmodules`'s (23) will
disagree with the checkout.

**How to apply:** do not add the submodule yourself — adding a new vendor pin
is the same "human decision, never an agent's" the repo already states for
bumping one. Surface it; don't silently fix it. Found 2026-09-21 while
reconciling README.md's vendor counts against the generated `docs/VENDOR.md`.
