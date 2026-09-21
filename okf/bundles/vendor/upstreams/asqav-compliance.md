---
type: Vendor Upstream
title: ASQAV Compliance Scanner
description: the five governance controls a CI scan checks agent code for
resource: https://github.com/Atomz-org/asqav-compliance
tags:
- vendor
- reference
- Elastic-2.0
status: stable
sources:
- id: asqav-compliance:src/scanner.ts
  resource: https://github.com/Atomz-org/asqav-compliance
  title: src/scanner.ts
- id: asqav-compliance:action.yml
  resource: https://github.com/Atomz-org/asqav-compliance
  title: action.yml
---

# ASQAV Compliance Scanner

It is a second opinion with a different failure mode. `pf provenance` is runtime evidence: it proves what the ledger recorded and can say nothing about code no agent has exercised yet. The scanner is static: it reads agent source and asks whether the controls are present at all, mapped to EU AI Act, DORA and ISO 42001. A control that exists but never runs is invisible to us and visible to it, and the reverse is equally true — which is the only reason to carry both.
The url is our own fork, and deliberately so. `jagmarques/asqav-compliance` was deleted on 18 September 2026 — the account with it — and for two days every `submodules: true` checkout in this repository failed at step one. The pinned commit `d57fccc` survived in GitHub's marketplace-validation mirror, `actions-marketplace-validations/jagmarques_asqav-compliance`, and `Atomz-org/asqav-compliance` is a fork of that at the same sha. Nothing was bumped: a git object name is a hash of the tree and its whole history, so a repository that can produce `d57fccc` is producing the bytes we already ran — that is the check, not the mirror owner's word. The fork exists because the mirror is no more permanent than the upstream was, and an unreachable pin costs the scan silently.

## Adopted

- **src/scanner.ts** (shape) -> platform/src/pf/provenance/ledger.py, platform/src/pf/provenance/audit.py
  Its five categories — audit trail, policy enforcement, revocation, human oversight, error handling — are the checklist our ledger is built to satisfy in behaviour rather than in vocabulary: `intent`/`decision`/ `execution` are the audit trail, `pf.loops.gate` the policy enforcement, `revoke`/`reinstate` the revocation, `approve` the human oversight. Ours differ in kind: the scanner matches identifiers, we record what actually happened and hash-link it.
- **action.yml** (data) -> .github/workflows/ai-governance.yml
  Run from the submodule path (`uses: ./vendor/asqav-compliance`) rather than by tag, so the code that judges our compliance is pinned like every other upstream here. Its inputs and outputs are the contract that workflow depends on; upstream renaming `score` or `gaps` breaks the job summary.

## Declined

- **the `asqav` runtime SDK (asqav / @asqav/sdk)**
  It ships actions to a hosted service, defaulting to hash-only mode against *.asqav.com. Our ledger is local, append-only and anchored to a public timestamp authority — an auditor verifies it with openssl and a 150-line stdlib script, trusting neither them nor us. Adding a third-party trust dependency to the evidence path would remove the one property the design exists for.
- **failing the build on the scanner's compliance score**
  It is regex over source. A file that mentions `revoke` in a comment scores as having revocation, and a correct implementation that spells it `disable_agent` scores as missing it. Useful as a prompt to go and look; wrong as a merge gate. `pf provenance verify` blocks instead, because it tests behaviour.
