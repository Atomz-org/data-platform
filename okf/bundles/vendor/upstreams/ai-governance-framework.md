---
type: Vendor Upstream
title: FINOS AI Governance Framework
description: the risk taxonomy and control catalogue, cross-walked to the regulators
resource: https://github.com/Atomz-org/ai-governance-framework
tags:
- vendor
- reference
- CC-BY-4.0
status: stable
sources:
- id: ai-governance-framework:docs/_mitigations
  resource: https://github.com/Atomz-org/ai-governance-framework
  title: docs/_mitigations
- id: ai-governance-framework:docs/_risks
  resource: https://github.com/Atomz-org/ai-governance-framework
  title: docs/_risks
- id: ai-governance-framework:docs/_data/references
  resource: https://github.com/Atomz-org/ai-governance-framework
  title: docs/_data/references
- id: ai-governance-framework:docs/_data/ai_deployment_model.yml
  resource: https://github.com/Atomz-org/ai-governance-framework
  title: docs/_data/ai_deployment_model.yml
- id: ai-governance-framework:docs/heuristic-assessment.md
  resource: https://github.com/Atomz-org/ai-governance-framework
  title: docs/heuristic-assessment.md
- id: ai-governance-framework:templates-for-ri-md/mi-template.md
  resource: https://github.com/Atomz-org/ai-governance-framework
  title: templates-for-ri-md/mi-template.md
---

# FINOS AI Governance Framework

It closes the fourth side of the governance question, and it is the only side that can be read by code.
`pf.provenance` is runtime evidence — what an agent did, hash-linked and anchored. `asqav-compliance` is static analysis — whether the controls exist in the source. `public-sector-ai-playbook` is the artefact a regulator is handed. None of the three says *which controls there are*, and none maps a control to the regulation it discharges. Before this, our ten `policy.yaml` entries were a list someone wrote down, and "does this satisfy the EU AI Act?" had no answer even though the evidence to answer it was already on disk.
This is that missing referent: 23 risks and 23 controls with a public, stable id scheme (`AIR-SEC-24`, `AIR-DET-21`), each carrying its own citations into the EU AI Act, ISO 42001, NIST SP 800-53r5, NIST AI 600-1, OWASP LLM/ML/ASI, FFIEC, SR 11-7, IOSCO and the UK and Canada regimes. Six of the risks (24-29) are specifically agentic — authorization bypass, tool-chain manipulation, MCP supply-chain compromise, state poisoning, multi-agent trust boundaries, credential harvesting — which is this platform's actual threat surface rather than a generic GenAI one.
Carried as `data` rather than `reference` because we read the frontmatter at runtime. That is deliberate: it makes an upstream rename a build failure instead of a slowly rotting mapping.
It is pinned as *a* catalogue, not *the* catalogue. `pf.air` reads control catalogues generally; this one is a `CatalogueSource` in `platform/src/pf/air/sources.py`, and a second — a sector regulator's, a tenant's own control library — is another such object on the `pf.catalogues` entry point of any installed distribution. Nothing in the parser, the coverage derivation, the gate or the CLI names FINOS. That matters here specifically because this platform is multi-tenant: a financial-services framework is the right default for some sisters and noise for others, and swapping it must not be a fork of the reader.

## Adopted

- **docs/_mitigations** (data) -> platform/src/pf/air/sources.py, platform/src/pf/air/catalogue.py
  23 control definitions. We read `sequence`, `type`, `title`, `doc-status`, `mitigates:` and every `<framework>_references:` list from the YAML frontmatter; the prose body below it is guidance for a human and we do not parse it. The public id is derived, not stored — `AIR-{type}-{sequence}` — which is why `type` changing from PREV to DET upstream renames a control, and why `pf air verify` checks the set of derived ids rather than trusting filenames.
- **docs/_risks** (data) -> platform/src/pf/air/sources.py, platform/src/pf/air/catalogue.py
  23 risk definitions, same frontmatter contract. Sequence numbers are non-contiguous (1, 2, 4-10, 14, 16-20, 22-29) because entries have been retired, so nothing here may assume a dense range.
- **docs/_data/references** (data) -> platform/src/pf/air/sources.py, platform/src/pf/air/catalogue.py
  13 crosswalk files, one per external regime, each an `entries:` mapping from a stable key to a title and canonical URL. These keys are the contract — upstream's own README says renaming one is breaking — and they are what turns "we enforce least privilege" into "we discharge EU AI Act Article 12 and NIST AC-6". `pf air verify` resolves every reference in every risk and control against these files and fails on the first dangling key.
- **docs/_data/ai_deployment_model.yml** (parity) -> platform/src/pf/air/register.py
  The taxonomy a project classifies itself against in `air.yaml` (`ai_type`, `architecture_pattern`, `workflow_pattern`, `agent_pattern`). Parity rather than data: we validate a project's declared profile against upstream's vocabulary, so an upstream that adds a pattern means a project may now describe itself more precisely, not that our build breaks.
- **docs/heuristic-assessment.md** (shape) -> platform/src/pf/air/register.py
  Its eight steps (use case, data, model, output impact, regulatory mapping, security, controls, decision) are the section order of the generated register. Ours answers the ones it can from the ontology and the ledger and leaves the rest to `air.yaml` — the difference between a form someone filled in and a report derived from the repository.
- **templates-for-ri-md/mi-template.md** (parity) -> platform/src/pf/air/sources.py
  The declared frontmatter contract for a control, and the reason our `Class` literal admits `RESP` even though no control uses it yet: the template says PREV|DET|RESP, so a response control appearing upstream must parse rather than crash.

## Declined

- **the Jekyll site (_layouts, _includes, style.css, single-page.html, _config.yml)**
  We render from the frontmatter, not from their templates. Adopting the Liquid layer would mean carrying a static-site generator to answer "which control covers this risk" — a question a dict already answers. `_config.yml` is the one near miss: it defines the RC/OP/SEC and PREV/DET type vocabularies. Those are eight literals, and copying them into `catalogue.py` where the parser can see them is clearer than reading a Jekyll config at runtime to learn two enums.
- **scripts/dl_eu-ai-act.py, dl_nist-pdfs.py, dl_owasp.py, dl_ffiec-itbooklets.py**
  They regenerate the crosswalk YAMLs by fetching regulator sites and PDFs. A build that reaches the open internet fails differently every day, and the reason to pin an upstream at all is that the version a regulator was shown is the version we still have. The vendored YAML *is* the pin; regenerating it is upstream's job, and it reaches us as a reviewed pin bump.
- **the four use cases (docs/_usecases — credit risk, wealth management, loan approval, financial crime)**
  They are worked examples of a *tenant's* business context, and this platform is multi-tenant. A loan-approval threat model belongs to the company doing loan approval, not to shared infra — the same reason the playbook's sector playbooks were declined and the same reason business logic never lives in platform/. A project that wants one fills in its own `air.yaml` profile; the framework's are reference reading.
- **registering the catalogue as a `pf.tools` Tool**
  The Tool seam is for capabilities that also run — a Dagster asset, a UI surface, a dbt binding — and this has none. It is also the wrong safety posture: a governance baseline that `pf tool disable` can switch off is not a baseline. It lands as a first-class module and CLI group, the same shape as `pf provenance` and `pf vendor`.
- **doc-status as a gate input**
  Every control we map is `Approved-Specification` today, and it is tempting to fail on anything less. Declined: upstream's status ladder (Pre-Draft, Draft, Working-Group-Approved, Approved-Specification) describes *their* consensus, and letting it decide whether our build passes would hand a FINOS working group a vote on our merge gate. It is parsed, reported by `pf air show`, and enforces nothing.
