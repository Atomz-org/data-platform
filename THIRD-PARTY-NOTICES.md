# Third-party notices

This repository is licensed under the Apache License 2.0 (see [LICENSE](LICENSE)).
It pins 21 upstream projects as read-only git submodules under `vendor/` and, in
some cases, adapts material from them into `platform/`. The authoritative,
per-path record of every borrowing — kind, pinned commit, and license — is
`platform/src/pf/vendor/registry.yaml` (`pf vendor list -v`, `pf vendor why <file>`).
This file summarises the license posture and discharges attribution obligations.

Submodules are **pointers, not copies**: cloning this repository without
`--recurse-submodules` fetches none of the upstream code. Each upstream retains
its own license, which governs its own code. What follows concerns material
*adapted into this repository's own files*.

## Adapted material and its attributions

| Upstream | License | What this repo took |
|---|---|---|
| [FINOS AI Governance Framework](https://github.com/finos/ai-governance-framework) (via Atomz-org fork) | CC BY 4.0 | Control/risk catalogue data and mitigation vocabularies, read at runtime and partially copied into `pf.air`. Credit line is emitted in every generated register (see `pf/air/sources.py`). |
| [OpenTopology](https://github.com/opentopology/opentopology) | Apache-2.0 | Relationship vocabulary verbatim (`governed_by`, `implemented_by`, `verified_by`); schema validated against in place, never copied. |
| [WrenAI](https://github.com/Canner/WrenAI) | Apache-2.0 (`core/`), CC BY 4.0 (`docs/`) | MDL field names and cardinality enum from `core/`; schema validated against in place. |
| [dbt-agent-skills](https://github.com/dbt-labs/dbt-agent-skills) | Apache-2.0 | Skill content rewritten against dbt Core + dbt-duckdb (9 ports). |
| [duckdb-skills](https://github.com/duckdb/duckdb-skills) | MIT | Skill content adapted (6 ports). |
| [dagster-skills](https://github.com/dagster-io/skills) | Apache-2.0 | Skill content adapted (2 ports). |
| [dlthub-ai-workbench](https://github.com/dlt-hub/dlthub-ai-workbench) | dltHub License (proprietary; see below) | Toolkit structure; skills independently rewritten against dlt Core's public Apache-2.0 API (8 ports). |
| [loop-engineering](https://github.com/cobusgreyling/loop-engineering) | MIT | Loop building blocks adapted (`pf/loops/`). |
| [recce-claude-plugin](https://github.com/DataRecce/recce-claude-plugin) | **none declared** (see below) | `recce-review` skill ported and cut down. |
| [forge](https://github.com/Webba-Creative-Technologies/forge) | MIT | Design-token names and the light/dark contract. |
| [Public Sector AI Playbook](https://github.com/PackMaaan/public-sector-ai-playbook) | CC BY 4.0 | Model-card and risk-register document structure, by Linda Oraegbunam. |

Upstreams pinned for **contract, drift-watch, or CLI invocation only** (no
material adapted into this repo): recce (Apache-2.0), recce-ui (Apache-2.0),
recce-pr-update (MIT), OpenMetadata and OpenMetadataStandards (Apache-2.0),
context-ontology-accelerator (Apache-2.0), ontology-playground (MIT),
shadcn-admin (MIT), evidence-bi (no upstream license declared — nothing copied,
submodule pointer only), asqav-compliance (Elastic License 2.0 — see below).

## Constraints to know about

- **recce-claude-plugin declares no license.** Verified against the GitHub API
  on 2026-08-19: no LICENSE file, no license field in its manifest — so the
  default is all-rights-reserved, and the ported `recce-review` skill is a
  derivative of unlicensed content. DataRecce's sibling repos are Apache-2.0
  and MIT, so this reads as upstream oversight; the fix is an upstream issue
  asking for a license, or an independent rewrite of the skill. Tracked in
  `registry.yaml` under `licence_review`.
- **WrenAI is tri-licensed with a pre-emptive AGPL-3.0.** As of 2026-08-19 the
  upstream path map assigns `core/**` (the MDL schema this repo drew field
  names from) to Apache-2.0, and **no path is AGPL yet** — the AGPL-3.0 text is
  staged for future modules. The `wrenai` PyPI package is Apache-2.0. A vendor
  pin bump that moves paths onto AGPL-3.0 is the event to watch for; the
  drift gate (`pf vendor drift`) is the mechanism that surfaces it.

- **asqav-compliance (Elastic License 2.0).** Executed unmodified from its
  submodule in CI (`.github/workflows/ai-governance.yml`). ELv2 forbids
  providing the software to third parties as a managed service: this platform
  must not expose the scanner as a compliance-scanning feature to its own
  tenants. Recorded in `registry.yaml` under `licence_review`.
- **dlthub-ai-workbench (proprietary dltHub License).** No source is copied;
  the registry records the dlt toolkits as independent rewrites against dlt
  Core's public API (dlt Core is Apache-2.0). The registry's own standing note
  applies: confirm scope-of-use with counsel. Recorded in `registry.yaml`
  under `licence_review`.

## Runtime dependencies

Python and npm dependencies are declared in `pyproject.toml` / `package.json`
and fetched from public registries; they are not vendored into this
repository. All direct dependencies carry permissive licenses (Apache-2.0,
MIT, BSD). dbt packages (`dbt_utils`, `dbt_date`, `dbt_expectations`,
`elementary`) are Apache-2.0 and fetched by `dbt deps`, never committed.
