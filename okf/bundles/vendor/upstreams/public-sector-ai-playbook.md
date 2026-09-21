---
type: Vendor Upstream
title: Public Sector AI Playbook
description: the governance artefacts a regulated deployment has to produce
resource: https://github.com/PackMaaan/public-sector-ai-playbook
tags:
- vendor
- reference
- CC-BY-4.0
status: stable
sources:
- id: public-sector-ai-playbook:05-deployment/model-card-template.md
  resource: https://github.com/PackMaaan/public-sector-ai-playbook
  title: 05-deployment/model-card-template.md
- id: public-sector-ai-playbook:04-governance/ai-risk-register-template.md
  resource: https://github.com/PackMaaan/public-sector-ai-playbook
  title: 04-governance/ai-risk-register-template.md
---

# Public Sector AI Playbook

It closes the third side of the governance question. `pf.provenance` is runtime evidence — what an agent actually did, hash-linked and anchored. `asqav-compliance` is static analysis — whether the controls exist in the code. Neither says what the controls should *be*, and for a regulated deployment that is the part someone external judges: a model card, a bias audit, a risk register, a supplier due-diligence trail, mapped to the UK AI Playbook (2025) and the EU AI Act.
Carried rather than copied because these are templates for a *deployment*, and this platform is multi-tenant: the risk register belongs to a company, not to the shared infra. The submodule is the reference a project fills in from, pinned so the version a regulator was shown is the version we still have.

## Adopted

- **05-deployment/model-card-template.md** (shape) -> platform/src/pf/provenance/audit.py
  The audit's four questions — integrity, completeness, coverage, oversight — are the evidence half of what a model card asks for. Ours answers them from the ledger rather than from a form, which is the difference between a document that asserts human oversight and a chain that shows the approval.
- **04-governance/ai-risk-register-template.md** (shape) -> gate.yaml
  A risk register names the controls; gate.yaml is the subset that is machine-enforced. Drift between the two is the thing to watch — a register entry with no gate rule is a control that exists only on paper, and that comparison is the reason to carry the template at all.

## Declined

- **tools/readiness_scorer.py**
  It is an interactive CLI that prompts for 25 answers and crashes on a non-TTY (no `--help`, no flags), so it cannot run in CI or from a loop. `pf.loops.audit` already scores readiness from the repository itself — hook present, graph built, card current — which is a measure nobody can talk up in an interview with themselves.
- **tools/governance_report_generator.py**
  Verified working (it generates a governance pack from a project JSON), and still not adopted: it reads a hand-written config, so the report says whatever the config claims. Ours would have to read the ontology and the ledger, and at that point it shares no code with this — only the output shape, which is what `adopted` above records.
- **the sector playbooks (healthcare, local government)**
  NHS DSPT, DCB0129 and MHRA/SaMD classification are real obligations for a healthcare deployment and noise for every other tenant. They belong to a project that has that regulator, not to shared infra — the same reason business logic never lives in platform/.
