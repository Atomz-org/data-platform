---
name: aidf-governance-and-dora-layer
description: 'pf.aidf: floor governs every entity (no overlay = floor, overlays only tighten); contracts validated in strict JSON mode; rejections are deny+blocked chain records; breaker state is read from the chain; scanners never workspace deps; forks absent on 2026-09-28; harness maps at budget'
type: project
status: active
agent: claude-code
---

`pf.aidf` (2026-09-28) is the runtime AI governance engine (`pf govern`) and
the DORA evidence audit (`pf dora`), reaching every entity through the
default-enabled `aidf` capability. docs/AIDF.md is the reference; these are the
traps it does not repeat.

**Why:** the blueprint asked for a root `governance/` package, a second
per-block ledger, a `compliance/` tree and three new workflows. Each already
had a home here, and building beside them would have produced a second chain
(AGENTS.md §7), a second gate and a second nightly issue cron racing the first.

**How to apply:**
- A project with no `governance/aidf.yaml` is governed by the floor
  (`pf/aidf/data/defaults.yaml`), not ungoverned. The seeded overlay is inert;
  overlays may only tighten (`AidfRelaxation` at load). `dora.sbom.ignore_unfixed`
  tightens by going *off*; the breaker flag tightens by going *on*.
- Contracts are validated in strict *JSON* mode (`pf.aidf.schemas.validate_payload`).
  Strict Python mode refuses `"SUM"` for an enum and an ISO string for a datetime,
  which is every agent payload; the engine and the tests both go through the helper.
- Rejections are a `deny` DECISION + `blocked` EXECUTION so `pf provenance verify`
  stays clean; the ledger gets the payload's sha256 and the findings, never the
  payload. The breaker's count is *read from the chain* (tool `aidf.metric`,
  payload `aidf_status`); `pf govern breaker --reset --reason` writes a marker
  (tool `aidf.breaker`). No side file, by design.
- Prowler, Trivy, sentence-transformers and guardrails-ai are commands or
  isolated installs, never workspace deps — the openmetadata antlr lesson. The
  Atomz-org forks of guardrails and prowler did not exist on 2026-09-28; the
  submodule commands are in docs/AIDF.md for a human to run into `vendor/`.
- `pf dora audit` reports `unverified` for anything it could not run; it is
  never a pass. Generated evidence lives in `**/governance/dora/` (gitignored,
  gate-denied, CI-archived with the matrix sha256 in the chain).
- The harness maps sit at their budget: jaffle-shop went 4002/4000 when the
  workflow was named `dora-compliance.yml` and is 3999 as `dora.yml`. The next
  addition to the "platform paths" workflow list must cap a section in
  `pf.harnessmap`, not rename things.
- `.tmp/wt/` is another session's worktree (branch feat(agents)--qwen-local);
  `pf memory check` flags its notes as outside every module. Not ours to delete.
